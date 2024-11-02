import requests
import csv
import time
from requests.exceptions import ConnectionError, Timeout
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# GitHub API token
GITHUB_TOKEN = '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'
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# Session with retry strategy
session = requests.Session()
retry_strategy = Retry(
    total=5,  # Retry up to 5 times
    backoff_factor=2,  # Exponential backoff
    status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP errors
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)

# Helper function to clean up company names
def clean_company_name(company):
    return company.strip().lstrip('@').upper() if company else None

# Function to fetch users from the GitHub API
def fetch_users(city="Chicago", min_followers=100):
    users = []
    page = 1

    while True:
        url = f"https://api.github.com/search/users?q=location:{city}+followers:>{min_followers}&page={page}&per_page=100"
        try:
            response = session.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            data = response.json()
        except (ConnectionError, Timeout) as e:
            print(f"Error fetching users on page {page}: {e}")
            time.sleep(5)  # Wait and retry
            continue
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")
            break

        # Break if no more results
        if 'items' not in data or not data['items']:
            break

        for user in data['items']:
            # Get full user info
            user_url = user['url']
            try:
                user_response = session.get(user_url, headers=HEADERS, timeout=10)
                user_response.raise_for_status()
                user_data = user_response.json()
            except (ConnectionError, Timeout) as e:
                print(f"Error fetching user info for {user['login']}: {e}")
                continue

            # Extract required fields
            users.append({
                'login': user_data['login'],
                'name': user_data['name'],
                'company': clean_company_name(user_data['company']),
                'location': user_data['location'],
                'email': user_data['email'],
                'hireable': user_data['hireable'],
                'bio': user_data['bio'],
                'public_repos': user_data['public_repos'],
                'followers': user_data['followers'],
                'following': user_data['following'],
                'created_at': user_data['created_at'],
            })

        page += 1
        time.sleep(1)  # Avoid hitting API rate limits

    return users

# Function to fetch repositories for a user
def fetch_repositories(user_login):
    repositories = []
    page = 1

    while True:
        url = f"https://api.github.com/users/{user_login}/repos?per_page=100&page={page}"
        try:
            response = session.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            repo_data = response.json()
        except (ConnectionError, Timeout) as e:
            print(f"Error fetching repositories for {user_login} on page {page}: {e}")
            time.sleep(5)  # Wait and retry
            continue

        # Break if no more repositories
        if not repo_data:
            break

        for repo in repo_data:
            repositories.append({
                'login': user_login,
                'full_name': repo['full_name'],
                'created_at': repo['created_at'],
                'stargazers_count': repo['stargazers_count'],
                'watchers_count': repo['watchers_count'],
                'language': repo['language'],
                'has_projects': repo['has_projects'],
                'has_wiki': repo['has_wiki'],
                'license_name': repo['license']['key'] if repo['license'] else None,
            })

        if len(repo_data) < 100:
            break

        page += 1
        time.sleep(1)  # Avoid hitting API rate limits

    return repositories

# Save users to CSV
def save_users_to_csv(users, filename="users.csv"):
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=users[0].keys())
        writer.writeheader()
        writer.writerows(users)

# Save repositories to CSV
def save_repositories_to_csv(repositories, filename="repositories.csv"):
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=repositories[0].keys())
        writer.writeheader()
        writer.writerows(repositories)

def main():
    print("Fetching users...")
    users = fetch_users()
    save_users_to_csv(users)
    print(f"Saved {len(users)} users to users.csv")

    print("Fetching repositories...")
    all_repositories = []
    for user in users:
        user_repos = fetch_repositories(user["login"])
        all_repositories.extend(user_repos)
        print(f"Fetched {len(user_repos)} repositories for user {user['login']}")

    save_repositories_to_csv(all_repositories)
    print(f"Saved {len(all_repositories)} repositories to repositories.csv")

if __name__ == "__main__":
    main()
