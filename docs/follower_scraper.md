# Follower Scraper Documentation

## Overview

The Follower Scraper module is responsible for collecting follower data from Instagram profiles. It handles navigating to follower lists, extracting follower information, and analyzing follower profiles.

## Features

- **Follower List Collection**: Navigates to a user's profile and extracts the complete list of followers
- **Infinite Scroll Handling**: Automatically scrolls through the follower list to load all followers
- **Profile Analysis**: Visits individual follower profiles to collect detailed information
- **Account Type Detection**: Identifies whether accounts are personal, business, or creator accounts
- **Privacy Status Detection**: Determines if accounts are public or private
- **Follower Categorization**: Categorizes followers based on various metrics
- **Bot Detection**: Flags potential bot accounts based on username patterns and other indicators

## Usage

### Basic Usage

```python
from src.scrapers.follower_scraper import FollowerScraper

# Initialize the scraper (uses logged-in user if target_username is None)
scraper = FollowerScraper(target_username="example_user")

# Run the scraper
followers_data = scraper.run()

# Access the collected data
for follower in followers_data:
    print(f"Username: {follower['username']}")
    print(f"Full name: {follower['fullname']}")
    print(f"Account type: {follower.get('account_type', 'unknown')}")
    print(f"Is private: {follower.get('is_private', False)}")
    print("---")
```

### Command Line Usage

You can also run the follower scraper from the command line:

```bash
# Collect followers for the logged-in user
python -m src.main --collect-followers

# Collect followers for a specific user
python -m src.main --collect-followers --target username
```

### Testing

To test the follower scraper:

```bash
python -m src.test_follower_scraper
```

## Data Structure

The follower data is stored as a list of dictionaries, with each dictionary containing information about a single follower:

```json
{
  "username": "example_user",
  "fullname": "Example User",
  "bio_preview": "This is a bio preview",
  "collected_at": "2023-03-16T12:34:56.789012",
  "detailed_profile_analyzed": true,
  "posts_count": 123,
  "followers_count": 456,
  "following_count": 789,
  "account_type": "personal",
  "is_private": false,
  "profile_analyzed_at": "2023-03-16T12:35:00.123456"
}
```

## Follower Categories

The scraper categorizes followers into several groups:

- **Potential Bots**: Accounts with suspicious username patterns or characteristics
- **Business Accounts**: Accounts identified as business profiles
- **Creator Accounts**: Accounts identified as creator profiles
- **Private Accounts**: Accounts with privacy settings enabled
- **Public Personal Accounts**: Personal accounts with public visibility
- **High Follower Accounts**: Accounts with a large number of followers
- **Low Engagement Potential**: Accounts that are likely to have low engagement

## Data Storage

Follower data is stored in the `data/followers` directory in both JSON and CSV formats:

- `{username}_followers_{timestamp}.json`: Raw follower data
- `{username}_follower_categories_{timestamp}.json`: Categorized follower data
- `{username}_followers_{timestamp}.csv`: CSV export for easy analysis

## Performance Considerations

- The scraper implements rate limiting and random delays to avoid detection
- By default, it only analyzes a subset of follower profiles in detail (up to 100) to avoid excessive requests
- The scraper saves intermediate results to prevent data loss in case of interruption

## Error Handling

The scraper includes robust error handling:

- Retries failed requests automatically
- Handles stale elements and other common Selenium exceptions
- Logs all errors for debugging purposes
- Saves data even if the process is interrupted 