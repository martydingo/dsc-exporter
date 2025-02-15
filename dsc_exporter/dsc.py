import requests, tarfile, io, os, asyncio, contextlib
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import datetime


class dsc:
    fastApiApp = FastAPI()
    def __init__(self, config):
        self.config = config
        
        self.fetchLabler()
        self.fetchMMDBs()
        self.buildDscDatatoolCommand()
        self.runDscDatatool()

    def fetchLabler(self):
        dnsParamsToYamlResp = requests.get("https://github.com/DNS-OARC/dsc-datatool/raw/develop/contrib/iana-dns-params-toyaml.py")
        if dnsParamsToYamlResp.status_code == 200:
            dnsParamsToYamlScript = dnsParamsToYamlResp.text
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exec(dnsParamsToYamlScript)
            
            lablerYamlContents = stdout.getvalue()
            
            open("labler.yaml", "w").write(lablerYamlContents)

    def fetchMMDBs(self):
        if not os.path.exists("GeoLite2-Country.mmdb") or not os.path.exists("GeoLite2-ASN.mmdb"):
         mmdbApiKey = self.config["maxmind_api_key"]
         mmdbBaseUri = f"https://download.maxmind.com/app/geoip_download?license_key={mmdbApiKey}&edition_id=GeoLite2"
         mmdbAsnUri = f"{mmdbBaseUri}-ASN&suffix=tar.gz"
         mmdbCountryUri = f"{mmdbBaseUri}-Country&suffix=tar.gz"

         mmdbCountryResponse = requests.get(mmdbCountryUri)
         if mmdbCountryResponse.status_code == 200:
             mmdbCountryTarfile = tarfile.open(fileobj=io.BytesIO(mmdbCountryResponse.content))
         else:
             print(mmdbCountryResponse.status_code)

         for filename in mmdbCountryTarfile.getmembers():
             print(filename)
             if ".mmdb" in str(filename):
                 mmdbCountryDB = open("GeoLite2-Country.mmdb", "wb").write(mmdbCountryTarfile.extractfile(filename).read())

         mmdbAsnResponse = requests.get(mmdbAsnUri)
         if mmdbAsnResponse.status_code == 200:
             mmdbAsnTarfile = tarfile.open(fileobj=io.BytesIO(mmdbAsnResponse.content))
         else:
             print(mmdbAsnResponse.status_code)

         for filename in mmdbAsnTarfile.getmembers():
             print(filename)
             if ".mmdb" in str(filename):
                 mmdbAsnDB = open("GeoLite2-ASN.mmdb", "wb").write(mmdbAsnTarfile.extractfile(filename).read())
                
        
    def buildDscDatatoolCommand(self):
        dscDatatoolCmd = ["dsc-datatool"]
        
        dscDatatoolCmd.append(f"--server \"{self.config['exporter']['server']}\"")
        
        dscDatatoolCmd.append(f"--node \"{self.config['exporter']['node']}\"")
        
        dscDatatoolCmd.append(f"--output \";Prometheus;file=metrics.txt;prefix={self.config['exporter']['prefix']}\"")
        
        for transformer in self.config['exporter']['transformers']:
            dscDatatoolCmd.append(f"--transform \"{transformer}\"")
        
        for generator in self.config['exporter']['generators']:
            if "client_subnet_country" in generator:
                generator = f"{generator};db=GeoLite2-Country.mmdb"
                
            dscDatatoolCmd.append(f"--generator \"{generator}\"")
        
        dscDatatoolCmd.append(f"--xml {self.config['exporter']['xmlPath']}")
        
        self.dscDatatoolCommand = " ".join(dscDatatoolCmd)

    def runDscDatatool(self):
        asyncio.get_event_loop().create_task(self.processXML())
    
    async def processXML(self):
        while True:
            print(f"{datetime.datetime.now()}: Running DSC Datatool")
            await asyncio.subprocess.create_subprocess_exec("/bin/bash", "-c", f"{self.dscDatatoolCommand}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)    
            await self.cleanXML()
            await asyncio.sleep(30)
            
    async def cleanXML(self):
        xmlDir = self.config["exporter"]["xmlPath"]
        xmlFiles = os.listdir(xmlDir)
        # 60 an hour, over 24 hours
        if len(xmlFiles) > 1440:
            for file in xmlFiles[:1440]:
                print(f"Removing {xmlDir}/{file}")
                os.remove(f"{xmlDir}/{file}")


    @fastApiApp.get("/")
    async def root():
        metrics = open("metrics.txt", "r")
        return PlainTextResponse(metrics.read())
