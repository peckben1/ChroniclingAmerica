import requests, csv, time, fitz, pandas as pd

# Template: "https://chroniclingamerica.loc.gov/search/pages/results/?andtext={searchTerms}&page={startPage?}&ortext={chronam:booleanOrText?}&year={chronam:year?}&date1={chronam:date?}&date2={chronam:date?}&phrasetext={chronam:phraseText?}&proxText={chronam:proxText?}&proximityValue={chronam:proximityValue?}&format=json"
# params template = {"state", "andtext", "page", "ortext", "year", "date1", "date2", "phrasetext", "proxText", "proximityValue", "format"}


# Function to attempt request.get robust to 500 errors
def get_attempt(base_url, get_params=None, attempts=10):
    status = 0
    j = 0
    while status != 200 and j < attempts:
        try:
            response = requests.get(base_url, params=get_params, allow_redirects=True)
            status = response.status_code
        except:
            print("get_attempt exception")
        j += 1
        time.sleep(0.5)
    return response

# Initialize list to store processed items
done_items = {'phrase': 'instances'}

# Set of subjects and their searches
subjects = {"Olmsted_Meta": [{"ortext": "Olmsted Olmstead"}]}

for subject in subjects.keys():

    # Add DC and json params to all searches
    for payload in subjects[subject]:
        payload["state"] = "District of Columbia"
        payload["format"] = "json"
        payload["rows"] = 99999

    # Actual search requests
    for payload in subjects[subject]:
        r = get_attempt('https://chroniclingamerica.loc.gov/search/pages/results/', payload)
        if r.status_code != 200:
            print("Could not search ", payload)
            continue

        # Convert results object from search to json
        results = r.json()
        print(payload, results["totalItems"], len(results['items']))

        # Iterate through items in results and generate metadata row
        for item in results['items']:
            
                # The item URL leads to the files
                url = item['url']
                urls = get_attempt(url)
                if urls.status_code != 200:
                    print("Could not retrieve " + url)
                    continue
                urls = urls.json()

                # Retrieval of the ocr
                text_url = urls['text']
                text_get = get_attempt(text_url)
                if text_get.status_code != 200:
                    print("Could not retrieve " + text_url)
                    continue
                text = text_get.content
                text = text.decode("utf-8")
                text = text.replace("\n", " ")
                text = text.replace(".", "")
                text = text.replace(",", "")
                text = text.replace("!", "")
                text = text.replace("?", "")
                text = text.replace("\'", "")
                text = text.replace("\"", "")
                text = text.replace(":", "")

                Olm = text.find("Olmste")

                while Olm != -1:
                    phrase = text[text.rfind(" ", 0, text.rfind(" ", 0, Olm-3))+1:text.find(" ", Olm)]
                    print(phrase)
                    if phrase in done_items.keys():
                        done_items[phrase] += 1
                    else:
                        done_items[phrase] = 1
                    Olm = text.find("Olmste", Olm+1)

        df = pd.DataFrame([done_items.keys(), done_items.values()])
        df = df.transpose()
        df.to_csv(f"./CA_{subject}.csv", header=False)