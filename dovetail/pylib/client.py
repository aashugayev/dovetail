import os
import logging
import inspect
import importlib
import configparser

logger = logging.getLogger(__name__)


class Client:
    """
    Compose configured API and service implementations into one client.

    The caller normally creates ``Client()`` without naming an implementation.
    The factory locates ``config.cfg`` beside the caller, or uses the explicit
    ``config_file`` keyword, then imports the module/class pair declared by the
    selected API and service sections.
    """
    
    def __new__(self, **kwargs):
        """
        Build a client whose method resolution combines both configured layers.

        The API layer supplies the request/response-facing behavior and the
        service layer supplies the transport behavior. Configuration values are
        passed into the resulting instance so transport settings such as
        ``service`` and ``version`` remain available as instance attributes.
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

        # Import implementations by configured module/class names so this
        # factory does not need to know which API or transport is selected.
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
        Read the selected API, service, and implementation settings.

        The project accepts both a literal ``[default]`` section and
        ConfigParser's special ``[DEFAULT]`` section. The ``[api]`` section
        describes the API implementation; the section named by ``client``
        describes the service implementation and its transport settings.
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
