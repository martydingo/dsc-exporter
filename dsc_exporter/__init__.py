import yaml, uvicorn
from .dsc import dsc 

class dsc_exporter:
    def __init__(self, configPath):
        self.config = self.__init_cfg__(configPath)
        @dsc.fastApiApp.on_event("startup")
        async def startupEvent():
            dsc(self.config)
            
        uvicorn.run(dsc.fastApiApp)
        
        

    def __init_cfg__(self, configPath: str):
        return yaml.full_load(open(configPath, "r"))
