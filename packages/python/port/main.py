import logging
from collections.abc import Generator
from port.script import process
from port.api.commands import CommandSystemExit
from port.api.file_utils import AsyncFileAdapter

# Configure logging for production debugging
# In Pyodide, this will output to the browser console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ScriptWrapper(Generator):
    def __init__(self, script):
        logger.debug("ScriptWrapper: Initialized")
        self.script = script

    def send(self, data):
        logger.debug(f"ScriptWrapper.send: Received data type={type(data).__name__}")
        # Automatically wrap JS file readers with AsyncFileAdapter
        if data and getattr(data, '__type__', None) == "PayloadFile":
            logger.debug("ScriptWrapper.send: Wrapping PayloadFile with AsyncFileAdapter")
            data.value = AsyncFileAdapter(data.value)

        try:
            command = self.script.send(data)
            logger.debug(f"ScriptWrapper.send: Script returned command type={type(command).__name__}")
        except StopIteration:
            logger.info("ScriptWrapper.send: Script completed (StopIteration)")
            return CommandSystemExit(0, "End of script").toDict()
        except Exception as e:
            logger.error(f"ScriptWrapper.send: Script error: {e}", exc_info=True)
            raise
        else:
            return command.toDict()

    def throw(self, type=None, value=None, traceback=None):
        logger.debug("ScriptWrapper.throw: Called")
        raise StopIteration


def start(data):
    logger.info(f"start: Beginning script execution with data={data}")
    script = process(data)
    logger.debug("start: Script generator created, returning wrapper")
    return ScriptWrapper(script)

if __name__ == "__main__":
    from port.helpers import main
    main()
