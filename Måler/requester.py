import requests
import json


def getSigfoxData(id: int, epoch="1581720002000"):
    """
    Get the latest messages 
    """
    epoch = str(int(epoch) + 1)     #Do not include sent epoch. Only after

    authentication = ("643d0041e0b8bb55976d44fe", "ca70a8def999c45aaf1a3fd5a56f2f58")       #Credentials

    if id == 0: sigID = "1D3711"
    if id == 1: sigID = "1D3712"

    url = f"https://api.sigfox.com/v2/devices/{sigID}/messages?limit={10}&since={epoch}"
    print(url)

    r = requests.get(url, auth=authentication)

    #params=parameter
    apiJSON = json.loads(r.text)
    #print(type(apiJSON), json.dumps(apiJSON, indent=4))

    messages = []
    for message in apiJSON["data"]:
        time = str(message["time"])[:-3]
        data = bytes.fromhex(message["data"]).decode()
        sigID = message["device"]["id"]
        messages.append((sigID, time, data))
    return messages

a = getSigfoxData(0)
for i in a:
    print(i)

