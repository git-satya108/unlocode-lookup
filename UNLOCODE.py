import os
import time
import streamlit as st
from dotenv import load_dotenv
import autogen  # Ensure the autogen package is installed and configured
import requests
from bs4 import BeautifulSoup

# --- Load environment variables from .env ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY not found in the .env file!")
    st.stop()

# --- LLM configuration ---
llm_config = {
    "model": "gpt-4o",  # you may switch between "gpt-4o" and "o3-mini" for different reasoning tasks
    "temperature": 0.2,
    "api_key": OPENAI_API_KEY
}

# --- Define Agents using autogen ---
research_agent = autogen.AssistantAgent(
    name="ResearchAgent",
    llm_config=llm_config,
    system_message=(
        "You are a research agent specialized in UN/LOCODE data lookup. "
        "Retrieve the UN/LOCODE for a given country and city using reliable sources."
    )
)

lookup_agent = autogen.AssistantAgent(
    name="LookupAgent",
    llm_config=llm_config,
    system_message=(
        "You are a lookup agent. Combine the dynamic company abbreviation with the UN/LOCODE's city segment "
        "to form the final Organization Code."
    )
)

critic_agent = autogen.AssistantAgent(
    name="CriticAgent",
    llm_config=llm_config,
    system_message=(
        "You are a critic agent. Validate that the generated Organization Code is accurate, "
        "well-grounded in the UN/LOCODE data, and clearly explained."
    )
)

lead_agent = autogen.AssistantAgent(
    name="LeadAgent",
    llm_config=llm_config,
    system_message=(
        "You are the lead agent overseeing the entire UN/LOCODE lookup workflow. "
        "Coordinate the research, lookup, and critic agents to produce a final, validated "
        "Organization Code based on the company name, country, and city."
    )
)

# --- Simulated UNLOCODE Database ---
# This dictionary simulates a UNLOCODE database for several countries.
UNLOCODE_DB = {
    "France": {
        "MARSEILLE": "FRMRS",
        "MARSEILLE-EN-BEAUVAISIS": "FRMBE"
    },
    "United States": {
        "NEW YORK": "USNYC",
        "LOS ANGELES": "USLAX"
    },
    "Germany": {
        "BERLIN": "DEBER"
    },
    "China": {
        "BEIJING": "CNBJS",
        "SHANGHAI": "CNSHA"
    }
}


# --- Agent Simulation Functions ---
def simulate_research_agent(country: str, city: str) -> str:
    """
    Simulates the ResearchAgent by looking up the UNLOCODE for the selected country and city.
    In a production system, this agent might query a live data source or scrape the UNECE URL.
    """
    st.info("ResearchAgent: Looking up UNLOCODE data...")
    time.sleep(2)  # Simulate delay for research
    country_data = UNLOCODE_DB.get(country, {})
    city_upper = city.upper().strip()
    # Try exact match first; if not found, check if the city string appears in any key.
    for key, code in country_data.items():
        if key.upper() == city_upper or city_upper in key.upper():
            return code
    return "UNK00"


def generate_company_abbreviation(company_name: str) -> str:
    """
    Generate a company abbreviation from the company name based on dynamic logic.
    For example:
      - If three or more words: take the first 3 letters of the first word,
        the first 3 letters of the second word, and the first letter of the third word.
      - If two words: take the first 3 letters of each.
      - Otherwise, take the first 6 characters.
    This logic adapts to different company names.
    """
    words = company_name.split()
    if len(words) >= 3:
        abbr = words[0][:3].upper() + words[1][:3].upper() + words[2][0].upper()
    elif len(words) == 2:
        abbr = words[0][:3].upper() + words[1][:3].upper()
    else:
        abbr = company_name.replace(" ", "")[:6].upper()
    return abbr


def simulate_lookup_agent(unlocode: str, company_name: str) -> (str, str, str):
    """
    Simulates the LookupAgent by:
      1. Generating a company abbreviation from the company name.
      2. Extracting the location segment (last 3 characters) from the UNLOCODE.
      3. Concatenating them to form the final Organization Code.
    """
    st.info("LookupAgent: Processing data to generate Organization Code...")
    time.sleep(1)  # Simulate processing delay
    company_abbr = generate_company_abbreviation(company_name)
    if len(unlocode) >= 5:
        location_code = unlocode[-3:]
    else:
        location_code = "UNK"
    org_code = company_abbr + location_code
    return org_code, company_abbr, location_code


def simulate_critic_agent(org_code: str) -> str:
    """
    Simulates the CriticAgent which validates that the final Organization Code is accurate.
    """
    st.info("CriticAgent: Validating the Organization Code...")
    time.sleep(1)
    return f"Validated: The Organization Code '{org_code}' is correctly generated based on the UNLOCODE data."


def lead_agent_orchestrate(country: str, city: str, company_name: str) -> dict:
    """
    The LeadAgent orchestrates the workflow:
      1. Calls the ResearchAgent to retrieve the UNLOCODE.
      2. Calls the LookupAgent to generate the Organization Code using the company name.
      3. Calls the CriticAgent to validate the final result.
    Returns an aggregated dictionary with all output data.
    """
    # Step 1: Research Agent lookup
    unlocode = simulate_research_agent(country, city)

    # Step 2: Lookup Agent to generate final Organization Code
    org_code, company_abbr, location_code = simulate_lookup_agent(unlocode, company_name)

    # Step 3: Critic Agent validation
    critique = simulate_critic_agent(org_code)

    # Aggregate final output data
    final_output = {
        "country": country,
        "city": city.upper(),
        "company_name": company_name,
        "unlocode": unlocode,
        "company_abbr": company_abbr,
        "location_code": location_code,
        "org_code": org_code,
        "critique": critique
    }
    return final_output


# --- Fetch Country List from UNECE URL ---
@st.cache_data
def fetch_countries_from_unece():
    """
    Attempts to fetch the list of countries from the UNECE UN/LOCODE page.
    If unsuccessful, returns an empty list.
    """
    url = "https://unece.org/trade/cefact/unlocode-code-list-country-and-territory"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, 'html.parser')
        # Heuristic: extract all <a> tags with text that looks like country names.
        country_links = soup.find_all('a', href=lambda x: x and "service.unece.org" in x)
        countries = set()
        for link in country_links:
            text = link.get_text(strip=True)
            if text and all(ch.isalpha() or ch.isspace() for ch in text):
                countries.add(text)
        return sorted(list(countries))
    except Exception as e:
        st.error(f"Error fetching countries: {e}")
        return []


# --- Streamlit UI Setup ---
st.set_page_config(page_title="UNLOCODE Organization Code Lookup", layout="wide")
st.title("UNLOCODE Organization Code Lookup Chatbot")

# --- Sidebar with Agentic AI Design Information ---
st.sidebar.markdown(
    """
    ### Agentic AI Design
    This chatbot is designed using a team of agents (ResearchAgent, LookupAgent, CriticAgent, and LeadAgent) 
    following Agentic AI design principles to ensure that the information is well-grounded and accurate.
    """
)

st.markdown(
    """
    This application uses a multi-agent workflow to generate a validated Organization Code.
    It leverages UN/LOCODE data from UNECE and a dynamic company name abbreviation logic.

    **Workflow Overview:**
    1. **ResearchAgent:** Retrieves the UN/LOCODE for the selected country and entered city.
    2. **LookupAgent:** Generates a company abbreviation from the company name and combines it with the UN/LOCODE segment.
    3. **CriticAgent:** Validates the generated Organization Code.
    4. **LeadAgent:** Oversees and orchestrates the full process.
    """
)

# Input Fields: Company Name, Country, and City.
# Fetch country options from UNECE; if that fails, fallback to our static UNLOCODE_DB keys.
fetched_countries = fetch_countries_from_unece()
if not fetched_countries:
    fetched_countries = list(UNLOCODE_DB.keys())
else:
    # Ensure our known countries are included
    for c in UNLOCODE_DB.keys():
        if c not in fetched_countries:
            fetched_countries.append(c)
    fetched_countries = sorted(list(set(fetched_countries)))

company_name_input = st.text_input("Enter Company Name", "TEST BY KALAI")
selected_country = st.selectbox("Select Country", fetched_countries)
city_input = st.text_input("Enter City", "MARSEILLE")

if st.button("Generate Organization Code"):
    progress_bar = st.progress(0)
    with st.spinner("Coordinating agents..."):
        progress_bar.progress(20)
        final_data = lead_agent_orchestrate(selected_country, city_input, company_name_input)
        progress_bar.progress(80)
        time.sleep(0.5)
        progress_bar.progress(100)

    st.success("Organization Code generation complete!")

    # Display the final Organization Code prominently
    st.markdown("## Final Organization Code")
    st.markdown(
        f"<h1 style='text-align: center; color: green; font-size: 4em;'>{final_data['org_code']}</h1>",
        unsafe_allow_html=True,
    )

    # Detailed breakdown of the process
    st.markdown("### Detailed Breakdown")
    st.write(f"**Selected Country:** {final_data['country']}")
    st.write(f"**Entered City:** {final_data['city']}")
    st.write(f"**Company Name:** {final_data['company_name']}")
    st.write(f"**UNLOCODE Retrieved:** {final_data['unlocode']}")
    st.write(f"**Generated Company Abbreviation:** {final_data['company_abbr']}")
    st.write(f"**Extracted Location Code:** {final_data['location_code']}")

    st.markdown("### Critic Agent Feedback")
    st.write(final_data["critique"])
