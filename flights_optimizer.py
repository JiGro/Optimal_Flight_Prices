import random
from bs4 import BeautifulSoup
from datetime import timedelta, datetime
import time
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


def browser_startup_sequence(requests_amount):
    # start browser
    options = webdriver.ChromeOptions()
    service = Service(executable_path=r'Google_Maps_Scraper/chromedriver')
    agents = ["Firefox/66.0.3", "Chrome/73.0.3683.68", "Edge/16.16299"]
    print("User agent: " + agents[(requests_amount % len(agents))])
    options.add_argument('--user-agent=' + agents[(requests_amount % len(agents))] + '"')
    options.add_experimental_option('prefs', {'intl.accept_languages': 'en,en_US'})
    options.add_argument("--lang=en_US");
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    return driver


# gucken ob die seite fertig ist
def page_has_loaded(driver):
    page_state = driver.execute_script('return document.readyState;')
    return page_state == 'complete'


# Set up flight scaper
def scrape_flights(origin, destination, startdate, days, requests_amount, result_df):
    #startdate = '2023-09-04'
    #days = 2
    #origin = 'BER'
    #destination = 'MAD'
    #requests_amount = 0

    enddate = datetime.strptime(startdate, '%Y-%m-%d').date() + timedelta(days)
    enddate = enddate.strftime('%Y-%m-%d')

    url = "https://www.kayak.de/flights/" + origin + "-" + destination + "/" + startdate + "/" + enddate + "?sort=bestflight_a&fs=stops=-2"
    print("\n" + url)

    driver = browser_startup_sequence(requests_amount)
    driver.get(url)

    time.sleep(5)

    # Cookie Consent
    try:
        print("*** Check Cookie Consent window ***")
        cookie_button = driver.find_element(By.XPATH, "//div[@role='button'][@aria-label='Schließen']")
        cookie_button.click()
        print("Cookie Button clicked")
    except:
        print("No Cookie window")

    time.sleep(random.randint(15,20))

    soup = BeautifulSoup(driver.page_source,"html.parser")

    # Find all results
    flight_results = soup.find_all('div', attrs={'class': 'nrc6'})

    first_deptime_lst, return_deptime_lst, first_arrtime_lst, return_arrtime_lst, price_lst = ([] for i in range(5))

    for flight in flight_results:
        # First leg
        first_flight = flight.find_all('li', attrs={'class': 'hJSA-item'})[0]
        first_deptime = first_flight.find("div", attrs={"class": "VY2U"}).find_all("span")[0].text
        first_deptime_lst.append(first_deptime)
        first_arrtime = first_flight.find("div", attrs={"class": "VY2U"}).find_all("span")[2].text
        first_arrtime_lst.append(first_arrtime)

        # Returning flight
        second_flight = flight.find_all('li', attrs={'class': 'hJSA-item'})[1]
        return_deptime = second_flight.find("div", attrs={"class": "VY2U"}).find_all("span")[0].text
        return_deptime_lst.append(return_deptime)
        return_arrtime = second_flight.find("div", attrs={"class": "VY2U"}).find_all("span")[2].text
        return_arrtime_lst.append(return_arrtime)

        # Price
        flight_price = flight.find('div', attrs={'class': "f8F1-above"}).text.replace("\xa0€","")
        price_lst.append(flight_price)

    df = pd.DataFrame({"origin": origin,
                       "destination": destination,
                       "startdate": startdate,
                       "enddate": enddate,
                       "price": price_lst,
                       "currency": "EUR",
                       "deptime_o": first_deptime_lst,
                       "arrtime_d": first_arrtime_lst,
                       "deptime_d": return_deptime_lst,
                       "arrtime_o": return_arrtime_lst
                       })
    result_df = pd.concat([result_df, df], sort=False)

    driver.close()
    time.sleep(2)
    return True, result_df


# Create empty result dataframes
flight_results = pd.DataFrame(columns=['origin', 'destination', 'startdate', 'enddate', 'deptime_o', 'arrtime_d', 'deptime_d', 'arrtime_o', 'currency', 'price'])

#For Testing purposes
airport_codes = ['NAS', 'SJO', 'PUJ', 'SJU']
destinations = ['Nassau', 'San Jose', 'Punta Cana', 'San Juan']
startdates = ['2023-09-22', '2023-09-29', '2023-10-06', '2023-10-06', '2023-10-13']
length_of_stay = [2, 3]
amount_of_requests = 0

for airport in airport_codes:
    for startdate in startdates:
        for length in length_of_stay:
            amount_of_requests += 1
            success = False
            while success is not True:
                success, flight_results = scrape_flights('TPA', airport, startdate, length, amount_of_requests, flight_results)
                amount_of_requests += 1

flight_results = flight_results.astype({"price": int}).reset_index(drop=True)

# Excel Generation
excel_string = ""
for destination in airport_codes:
    excel_string += f"_{destination}"
flight_results.to_excel(f"Trip_Summary{excel_string}.xlsx")

# Find the minimum price for each destination-startdate-combination
flight_results_agg = flight_results.groupby(['destination', 'startdate'])['price'].min().reset_index().rename(
    columns={'min': 'price'})

# Prepare Heatmap data
flight_heatmap_results = pd.pivot_table(flight_results_agg, values='price',
                                        index=['destination'],
                                        columns='startdate')

# Create heatmap
sns.set(font_scale=1.5)
plt.figure(figsize=(18, 6))
svm = sns.heatmap(flight_heatmap_results, annot=True, annot_kws={"size": 24}, fmt='.0f', cmap="RdYlGn_r")
figure = svm.get_figure()
figure.savefig(f"Heatmap{excel_string}.png", dpi=400)
