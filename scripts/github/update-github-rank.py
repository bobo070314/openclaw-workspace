"""GitHub Top Projects Rank Updater.

This script automates the process of fetching the latest GitHub top projects
from the official API and updating the local CSV file.
"""

import csv
from datetime import datetime

import requests


def fetch_top_projects(limit=100):
    """Fetch the top GitHub repositories using the GitHub API."""
    url = f"https://api.github.com/search/repositories?sort=stars&order=desc&q=language:Python+language:JavaScript+language:TypeScript&per_page={limit}"
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return []

        data = response.json()
        repos = []
        for item in data["items"]:
            repo = {
                "rank": len(repos) + 1,
                "name": item["full_name"],
                "stars": item["stargazers_count"],
                "language": item["language"],
                "description": item["description"],
                "url": item["html_url"],
            }
            repos.append(repo)
        return repos
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        return []


def write_to_csv(repos, filename="github-top-projects.csv"):
    """Write the list of repositories to a CSV file."""
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["rank", "name", "stars", "language", "description", "url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for repo in repos:
            writer.writerow(
                {
                    "rank": repo["rank"],
                    "name": repo["name"],
                    "stars": repo["stars"],
                    "language": repo["language"],
                    "description": repo["description"],
                    "url": repo["url"],
                }
            )
    print(f"Successfully wrote {len(repos)} projects to {filename}")


def main():
    print("Starting GitHub top projects update...")
    repos = fetch_top_projects(100)
    if repos:
        write_to_csv(repos)
        # Update the markdown report
        with open("reports/github-top-100.md", "r", encoding="utf-8") as f:
            content = f.read()

        # Insert current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        updated_content = content.replace(
            "# GitHub Top 100 Open Source Projects (Updated)",
            f"# GitHub Top 100 Open Source Projects (Updated - {timestamp})",
        )

        with open("reports/github-top-100.md", "w", encoding="utf-8") as f:
            f.write(updated_content)

        print("Update completed. Report has been refreshed.")
    else:
        print("No data retrieved. Skipping update.")


if __name__ == "__main__":
    main()
