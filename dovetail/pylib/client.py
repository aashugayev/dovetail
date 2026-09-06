import os
import logging
import inspect
import importlib
import configparser

logger = logging.getLogger(__name__)

class Client:
    """
    Generic Client class to manufacture api-specific client class based on config file api service default settings
    """
    
    def __new__(self, **kwargs):
        """
        api and service specific client object factory
        """
        
        logger.debug("Received configuration=%s", kwargs) 
        
        if 'config_file' in kwargs:
            config_file = kwargs['config_file']
        else:
            caller_path, _ = os.path.split(os.path.realpath(inspect.stack()[1].filename))
            config_file = os.path.join(caller_path, 'config.cfg')

        config_conf = self.get_config_conf(config_file)
        config_conf.update(kwargs)

        if 'api_module' not in config_conf or 'api_class' not in config_conf:
            msg = "Unable to detect API implementation; configure api_module and api_class"
            logging.fatal(msg)
            raise RuntimeError(msg)

        if 'service_module' not in config_conf or 'service_class' not in config_conf:
            msg = "Unable to detect service implementation; configure service_module and service_class"
            logging.fatal(msg)
            raise RuntimeError(msg)

        api_module = importlib.import_module(config_conf['api_module'])
        api_client = getattr(api_module, config_conf['api_class'])
        service_module = importlib.import_module(config_conf['service_module'])
        service_client = getattr(service_module, config_conf['service_class'])
        logger.debug(
            "Implementing api=%s service=%s",
            config_conf['api_module'],
            config_conf['service_module'],
        )
        
        return type('Client', (api_client, service_client), config_conf)()

    @staticmethod
    def get_config_conf(config_file: str) -> dict:
        """
        collect default api interface configuration dictionary from config file
        """
        
        config_conf = dict()
        
        if os.path.exists(config_file) and os.path.isfile(config_file):
            config = configparser.ConfigParser()
            config.read(config_file)
            config_sections = config.sections()

            if 'default' in config_sections:
                default_section = config['default']
            elif config.defaults():
                default_section = config.defaults()
            else:
                default_section = None

            if default_section is not None:
                api = default_section.get('api')
                client = default_section.get('client')
                if api:
                    config_conf['api'] = api
                    if 'api' in config_sections:
                        api_section = config['api']
                        config_conf.update(dict(api_section))
                        config_conf['api_module'] = api_section.get('module')
                        config_conf['api_class'] = api_section.get('class')
                if client:
                    config_conf['client'] = client
                    if client in config_sections:
                        service_section = config[client]
                        config_conf.update(dict(service_section))
                        config_conf['service_module'] = service_section.get('module')
                        config_conf['service_class'] = service_section.get('class')
                for key in ('api_module', 'api_class', 'service_module', 'service_class'):
                    if key in default_section:
                        config_conf[key] = default_section[key]
            else:
                logger.warning(f"config file={config_file} 'default' section is missing from config sections={config_sections}")
        else:
            logger.warning(f"Unable to locate default configuration file={config_file}")
        
        logger.debug("configuration api=%s", config_conf)
        return config_conf
