# Simulation Mode

## Overview
The Instagram Ghost Follower Detection System includes a simulation mode that allows you to generate realistic engagement data for testing and development purposes without requiring actual Instagram API access or browser automation.

## Benefits
- **Development without API Access**: Test and develop the system without needing to connect to Instagram
- **Faster Testing**: Avoid the time-consuming process of browser automation and data scraping
- **Reproducible Results**: Generate consistent test data for debugging and development
- **Offline Development**: Work on the system without an internet connection

## Usage

### Command Line
To use simulation mode from the command line:

```bash
# Simulate engagement data only
python -m src.main --simulate --target <username>

# Simulate engagement data and analyze it
python -m src.main --simulate --analyze-engagement --target <username>
```

### Programmatic Usage
You can also use the simulation mode programmatically:

```python
from src.scrapers.engagement_scraper import EngagementScraper

# Initialize the scraper
scraper = EngagementScraper("username")

# Simulate engagement data
engagement_data = scraper.simulate_engagement_data()

# Process the data as needed
print(f"Generated {len(engagement_data['post_engagement'])} simulated posts")
```

## How It Works

The simulation mode:

1. Loads existing follower data from the `data/followers` directory
2. Generates random engagement data for:
   - Posts (default: 5 posts)
   - Stories (default: 1 story)
   - Reels (default: 3 reels)
   - Online activity (default: 50 records)
3. Saves the simulated data to the standard data files:
   - `data/<username>_post_engagement.json`
   - `data/<username>_story_engagement.json`
   - `data/<username>_reel_engagement.json`
   - `data/<username>_online_activity.json`

## Customization

The simulation parameters can be customized by modifying the `simulate_engagement_data` method in `src/scrapers/engagement_scraper.py`. You can adjust:

- Number of posts, stories, and reels to simulate
- Engagement rates and distributions
- Types of engagement (likes, comments, views)
- Online activity patterns

## Limitations

- Simulated data is randomly generated and may not perfectly reflect real-world engagement patterns
- Some advanced features like comment text analysis may not be fully simulated
- The simulation does not include profile images or media content

## Testing

A dedicated test script is available to verify the simulation functionality:

```bash
python -m src.test_simulate_engagement
```

This script runs the simulation, processes the data, and verifies that ghost followers can be correctly identified from the simulated data. 