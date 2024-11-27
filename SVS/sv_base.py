import time
import csv
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dictionary import brand_urls
import random
import re

# Setup ChromeDriver options
options = Options()
options.add_argument("--headless")  # Uncomment to run Chrome in headless mode (no GUI)
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920x1080")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# Initialize the WebDriver
driver = webdriver.Chrome(options=options)

# Get the current date and format it
currentDate = datetime.now().strftime("%Y-%m-%d")
# Define the CSV file name
csvFile = f"standvirtual_scraper_{currentDate}.csv"

# CONSTS
CLASS_DICT = {
    "num_cars" : "e17gkxda2 ooa-17owgto er34gjf0",
    "car_title": "ooa-1qo9a0p epwfahw6",
    "car_info": "ooa-d3dp2q epwfahw2",

    "brand": "efpuxbr9 ooa-1ed90th er34gjf0",
    "kilometer": {"data-parameter": "mileage"},
    "gasType": {"data-parameter": "fuel_type"},
    "gearBox": {"data-parameter": "gearbox"},
    "year": {"data-parameter": "first_registration_year"},
    "price": "ooa-2p9dfw efpuxbr4"
}

# Open the CSV file in write mode to create it fresh
with open(csvFile, mode='w', newline='', encoding='utf-8-sig') as file:
    # Create a CSV DictWriter object with the specified column order
    writer = csv.DictWriter(file, fieldnames=["Brand", "Title", "Kilometer", "Gas Type", "Gear Box", "Year", "Price"])

    # Write the header row
    writer.writeheader()

    # Open the base URL once to handle cookie consent
    driver.get("https://www.standvirtual.com/carros/")
    time.sleep(random.uniform(3,7))  # Allow the page to load

    # Handle "Accept Cookies" prompt
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Aceito')]"))
        ).click()
        print("Accepted cookies.")
    except Exception as e:
        print(f"No cookie consent prompt found or error clicking it: {e}")

    # Loop through each brand from the dictionary
    for brand, slug in brand_urls.items():
        print(f"Scraping listings for {brand}...")

        # Base URL for pagination (start at page 1)
        baseUrl = f"https://www.standvirtual.com/carros/{slug}?page=1"
        driver.get(baseUrl)
        time.sleep(5)  # Allow the page to load

        # Take a screenshot after loading the brand's page
        driver.save_screenshot(f"debug_{brand}.png")

        while True:
            # Get the page source and parse it with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")

            print(f"Scraping {driver.current_url} for {brand}...")

            totalCarsforBrand_el = soup.find("p", class_=CLASS_DICT["num_cars"])
            print(f'Total cars for {brand}: {totalCarsforBrand_el.b.contents[0]}')

            # Find all articles containing car information
            insideArticles = soup.find_all("section", class_="ooa-qat6iw epwfahw1")

            # Check if there are any listings
            if not insideArticles:
                print(f"No listings found for {brand}.")
                break  # Exit the loop if there are no listings

            # Loop through each article (car listing)
            for article in insideArticles:
                try:

                    # TODO: Find a way to create a dict of callables, so that each value will run a set of instructions
                    def generate_car_data_dict(brand: str, article):
                        car_data_dict = {}

                        car_data_dict["brand"] = brand

                        car_title_section = article.find("div", class_=CLASS_DICT["car_title"])

                        # Find the ad title
                        try:
                            car_data_dict["title"] = car_title_section.h1.a.stripped_strings[0]
                        except Exception as e:
                            car_data_dict["title"] = ''
                            print(f"Error getting title: {e}")

                        # Find the cilinder size and horse power
                        try:
                            cilinder_size_and_horse_power_string = car_title_section.p.string
                            pattern = r"(?P<cylinder>\d{1,3}\s?\d{3})\s*cm3\s*•\s*(?P<horsepower>\d+)\s*cv"
                            match = re.search(pattern, cilinder_size_and_horse_power_string)

                            if match:
                                car_data_dict["cilinder"] = match.group('cylinder').replace(' ', '')  # Removes any spaces within the cylinder size
                                car_data_dict["hp"]       = match.group('horsepower')
                        except Exception as e:
                            car_data_dict["cilinder"] = ''
                            car_data_dict["hp"] = ''
                            print(f"Error getting title: {e}")

                        car_info_section = article.find("div", class_=CLASS_DICT["car_info"]).dl

                        kilometer = car_info_section.find("dd", {"data-parameter": "mileage"})
                        kilometer = kilometer.string.replace(" km", "").replace(" ","") if kilometer else "1"

                        gasType = article.find("dd", {"data-parameter": "fuel_type"})
                        gasType = gasType.text if gasType else "N/A"

                        gearBox = article.find("dd", {"data-parameter": "gearbox"})
                        gearBox = gearBox.text if gearBox else "N/A"

                        year = article.find("dd", {"data-parameter": "first_registration_year"})
                        year = year.text if year else "N/A"

                        price = article.find("div", class_="ooa-2p9dfw efpuxbr4")
                        price = price.text.replace("EUR", "").replace(" ","").strip() if price else "N/A"

                        return car_data_dict

                    car_data_row = generate_car_data_dict(brand, article)

                    # Write data to CSV file immediately
                    writer.writerow(car_data_row)
                except Exception as e:
                    print(f"Error scraping a listing: {e}")
                    continue

            # Attempt to find the "Next Page" button
            try:
                next_button = driver.find_element(By.XPATH, "//li[@title='Next Page']")

                # Check if 'aria-disabled' is set to 'true' to detect the last page
                if next_button.get_attribute("aria-disabled") == "true":
                    print(f"No more pages for {brand}.")
                    break  # Exit the loop if the button is disabled

                # Scroll to the next button (make sure it's in view)
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)

                # Use JavaScript to click the next button (bypass overlay issues)
                driver.execute_script("arguments[0].click();", next_button)

                # Add a short delay to wait for the page to load
                time.sleep(3)

            except Exception as e:
                print(f"No next button found for {brand}")
                break  # Exit the loop if there's an issue with the next button

print(f"Scraping completed. Ads saved to '{csvFile}'.")

# Close the Selenium driver
driver.quit()
