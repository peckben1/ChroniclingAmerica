import requests, csv, time, fitz

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

# Initialize list to store processed items and PDF number iterator
done_items = dict()
i = 3533

# Set of subjects and their searches
subjects = {
    "Street_Extension2": [{"phrasetext": "permanent system of highways", "ortext": "engineer"},{"phrasetext": "street extension"}, {"phrasetext": "extension of highways"}]
    # "Hornblower_Marshall": [{"proxtext": "Hornblower architect"}, {"proxtext": "Hornblower Marshall"}], 
    # "Olmsted_Firm": [{"proxtext": "Olmsted architect"}, {"proxtext": "Olmstead architect"}, {"proxtext": "Olmsted Brothers"}, {"proxtext": "Olmstead Brothers"}, {"proxtext": "Olmsted Eliot"}, {"proxtext": "Olmstead Eliot"}], 
    # "JC_Olmsted": [{"proxtext": "John Olmsted", "proximityvalue": "2"}, {"proxtext": "J Olmsted", "proximityvalue": "2"}, {"proxtext": "John Olmstead", "proximityvalue": "2"}, {"proxtext": "J Olmstead", "proximityvalue": "2"}], 
    # "FL_Olmsted": [{"proxtext": "Fred Olmsted", "proximityvalue": "2"}, {"proxtext": "F Olmsted", "proximityvalue": "2"}, {"proxtext": "Fred Olmstead", "proximityvalue": "2"}, {"proxtext": "F Olmstead", "proximityvalue": "2"}, {"proxtext": "Frederick Olmsted", "proximityvalue": "2"}, {"proxtext": "Frederick Olmstead", "proximityvalue": "2"}, {"proxtext": "Fredk Olmsted", "proximityvalue": "2"}, {"proxtext": "Fredk Olmstead", "proximityvalue": "2"}, {"proxtext": "Frederic Olmsted", "proximityvalue": "2"}, {"proxtext": "Frederic Olmstead", "proximityvalue": "2"}]
    }

for subject in subjects.keys():
    # Initialize outfile and header row
    outfile = open("CA_" + subject + ".csv", "w", encoding='utf-8')
    outwriter = csv.writer(outfile)
    out_list = ["Newspaper", "Date", "Link", "PDF", "Search"]
    outwriter.writerow(out_list)

    # Add DC and json params to all searches
    for payload in subjects[subject]:
        payload["state"] = "District of Columbia"
        payload["format"] = "json"
        payload["rows"] = 50
        payload["page"] = "1"

    # Actual search requests
    for payload in subjects[subject]:
        not_done = True
        page_num = 1
        while not_done:
            r = get_attempt('https://chroniclingamerica.loc.gov/search/pages/results/', payload)
            if r.status_code != 200:
                print("Could not search ", payload)
                break

            # Convert results object from search to json
            results = r.json()
            print(payload, results["totalItems"], len(results['items']))
            if page_num * payload["rows"] >= results["totalItems"]:
                not_done = False
            else:
                page_num += 1
                payload["page"] = page_num

            # Iterate through items in results and generate metadata row
            for item in results['items']:
                out_list = []

                # "title" is the name of the newspaper
                out_list.append(item["title"])

                # This parses the date from the ID
                out_list.append(item["id"].split("/")[3])

                # Link to document
                out_list.append("https://chroniclingamerica.loc.gov" + item["id"])

                if item["id"] not in done_items.keys():
                    i += 1
                    done_items[item["id"]] = i

                    # The item URL leads to the files
                    url = item['url']
                    urls = get_attempt(url)
                    if urls.status_code != 200:
                        print("Could not retrieve " + url)
                        continue
                    urls = urls.json()

                    # Retrieval of the pdf
                    pdf_url = urls['pdf']
                    pdf_name = "./PDFs/PDF" + str(i) + ".pdf"
                    out_list.append("PDF" + str(i))
                    pdf_get = get_attempt(pdf_url)
                    if pdf_get.status_code != 200:
                        print("Could not retrieve " + pdf_name)
                        continue
                    open(pdf_name, 'wb').write(pdf_get.content)

                    # Open pdf with PyMuPDF and highlight search terms
                    pages = 0
                    while not pages:
                        pdf_doc = fitz.open(pdf_name)
                        pages = pdf_doc.pageCount
                    page = pdf_doc[0]
                    # Set of terms to highlight
                    highlight_text = [
                        "Olmsted",
                        "Olmstead",
                        "highway",
                        "extension"
                    ]
                    for text in highlight_text:
                        text_instances = page.searchFor(text)
                        for inst in text_instances:
                            highlight = page.addHighlightAnnot(inst)

                    # Incremental save
                    pdf_doc.saveIncr()

                # If already in done items, append PDF #
                else:
                    out_list.append("PDF" + str(done_items[item["id"]]))

                # Search which generated hit
                out_list.append(payload)
                
                # Write row
                outwriter.writerow(out_list)

    outfile.close()