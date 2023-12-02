import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import fsspec
from datetime import datetime
import sys


def load_county_shapes():
    c = "https://github.com/babdelfa/gis/blob/main/counties_geometry.zip?raw=true"
    with fsspec.open(c) as file:
        county_shapes = gpd.read_file(file)
    return county_shapes


def load_covid_data():
    url_cases = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv"
    df_cases = pd.read_csv(url_cases)

    url_deaths = "https://github.com/CSSEGISandData/COVID-19/raw/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv"
    df_deaths = pd.read_csv(url_deaths)

    return df_cases, df_deaths


def melt_and_merge_data(df_cases, df_deaths):
    drop_columns = ["UID", "iso2", "iso3", "code3", "Country_Region", "Lat", "Long_"]
    df_cases.drop(columns=drop_columns + ["FIPS"], inplace=True)
    df_deaths.drop(columns=drop_columns + ["FIPS"])

    rename_columns = {"Admin2": "county", "Province_State": "state", "Combined_Key": "county_state"}
    df_cases.rename(columns=rename_columns, inplace=True)
    df_deaths.rename(columns=rename_columns, inplace=True)

    id_vars_cases = ["county", "state", "county_state"]
    df_cases_melted = pd.melt(df_cases, id_vars=id_vars_cases, var_name="date", value_name="cases")

    id_vars_deaths = ["county", "state", "county_state", "Population", "FIPS"]
    df_deaths_melted = pd.melt(df_deaths, id_vars=id_vars_deaths, var_name="date", value_name="deaths")

    df = pd.merge(df_cases_melted, df_deaths_melted)
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%y")

    # Filter the DataFrame to include only dates up to and including 12/31/2022
    df = df[df["date"] <= "12/31/2022"]

    return df


def get_county_input(df):
    print("*** MIS 433 COVID19 Report ***")
    county_input = input("Enter County: ").capitalize()

    county_matches = df[df["county"] == county_input]
    if len(county_matches) > 1:
        unique_states = county_matches["state"].unique()

        if len(unique_states) == 1:
            state_input = unique_states[0]
        else:
            print(f"Multiple states found for the county '{county_input}'. Choose a state:")
            for i, state in enumerate(unique_states, start=1):
                print(f"{i}. {state}")

            state_choice = int(input("\nEnter the number corresponding to the desired state: "))
            print()
            if 1 <= state_choice <= len(unique_states):
                state_input = unique_states[state_choice - 1]
            else:
                print("Invalid choice. Exiting.")
                sys.exit()
    elif len(county_matches) == 1:
        state_input = county_matches["state"].iloc[0]
    else:
        print(f"No matching county found for '{county_input}' in the dataset.")
        sys.exit()

    return county_input, state_input


def get_population(df_county):
    population = df_county["Population"].iloc[0]
    formatted_population = "{:,}".format(population)
    print(f"Population of {county_input}, {state_input}: {formatted_population}\n")
    return population


def get_first_reported_date(df_county):
    first_reported_date = df_county.loc[df_county["cases"] > 0, "date"].min()
    formatted_date = first_reported_date.strftime("%B %d, %Y")
    print(f"First Reported Outbreak in {county_input}: {formatted_date}\n")
    return first_reported_date


def calculate_daily_new_cases(df_county):
    df_county = df_county.sort_values(by="date")
    df_county["new_cases"] = df_county["cases"].diff().fillna(0)
    return df_county


def calculate_average_and_total_new_cases(df_county):
    df_2020 = df_county[df_county.date.dt.year == 2020].copy()
    df_2021 = df_county[df_county.date.dt.year == 2021].copy()
    df_2022 = df_county[df_county.date.dt.year == 2022].copy()

    average_new_cases_2020 = round(df_2020["new_cases"].mean(), 2)
    average_new_cases_2021 = round(df_2021["new_cases"].mean(), 2)
    average_new_cases_2022 = round(df_2022["new_cases"].mean(), 2)

    total_new_cases_2020 = df_2020["new_cases"].sum()
    round_total_new_cases_2020 = round(total_new_cases_2020)
    total_new_cases_2021 = df_2021["new_cases"].sum()
    round_total_new_cases_2021 = round(total_new_cases_2021)
    total_new_cases_2022 = df_2022["new_cases"].sum()
    round_total_new_cases_2022 = round(total_new_cases_2022)
    cumulative_total_cases = df_county["cases"].iloc[-1]

    print(f"{county_input} County COVID19 Summary Statistics:")
    print(f" - Average number of new cases in 2020: {average_new_cases_2020}")
    print(f" - Average number of new cases in 2021: {average_new_cases_2021}")
    print(f" - Average number of new cases in 2022: {average_new_cases_2022}")
    print(f" - Total number of new cases in 2020: {format(round_total_new_cases_2020, ',')}")
    print(f" - Total number of new cases in 2021: {format(round_total_new_cases_2021, ',')}")
    print(f" - Total number of new cases in 2022: {format(round_total_new_cases_2022, ',')}")
    print(f" - Cumulative total number of cases: {format(cumulative_total_cases, ',')} (December 31, 2022)\n\n")


def plot_county_cases_over_time(df_county):
    df_cou = df_county.groupby("date", as_index=False)[["cases", "deaths"]].sum()

    plt.style.use("ggplot")
    fig, ax = plt.subplots()

    import matplotlib.dates as mdates
    ax.yaxis.get_major_formatter().set_scientific(False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    ax.plot(df_cou["date"], df_cou["cases"], color="red")
    ax.set_ylabel("Total Number of Cases")
    ax.set_xlabel("Date")
    ax.set_title(f"Total COVID-19 Cases for {county_input} County")
    plt.xticks(rotation=45)
    plt.show()


def create_county_map(merged_gdf, state_input):
    print(f"Interactive map of {state_input} counties and total COVID19 cases as of 12/31/22:")

    # Create an interactive map with the adjusted bounding box
    map_path = f"{state_input}_covid_map.html"
    merged_gdf.explore(column="Total Cases", cmap="Set2", legend=True, scheme="EqualInterval").save(map_path)
    print(f"Map saved to: {map_path}") 


# Main Program
county_shapes = load_county_shapes()
df_cases, df_deaths = load_covid_data()
df = melt_and_merge_data(df_cases, df_deaths)

county_input, state_input = get_county_input(df)
df_county = df[(df["county"] == county_input) & (df["state"] == state_input)]

population = get_population(df_county)
first_reported_date = get_first_reported_date(df_county)

df_county = calculate_daily_new_cases(df_county)
calculate_average_and_total_new_cases(df_county)
plot_county_cases_over_time(df_county)

df_final = df.drop(columns=["date"])
merged_df = pd.merge(county_shapes, df_final, left_on="FIPS_BEA", right_on="FIPS")
merged_df = merged_df[merged_df.state == state_input]

grouped_df = merged_df.groupby("county_state").agg(
    {"Population": "last", "cases": "last", "geometry": "first"}
).reset_index()

grouped_df = grouped_df.rename(columns={"county_state": "Location", "cases": "Total Cases"})
merged_gdf = gpd.GeoDataFrame(grouped_df, geometry="geometry", crs="4326")

create_county_map(merged_gdf, state_input)
