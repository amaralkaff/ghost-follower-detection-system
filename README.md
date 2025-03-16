# InstaLy Ghost Follower Detection System

## Project Overview
This system uses web scraping and machine learning to identify and report "ghost followers" - accounts that follow you but don't engage with your content. The pipeline automatically collects data from Instagram posts, stories, and reels, analyzes engagement patterns, and generates reports to help you identify inactive followers.

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd instagram-ghost-follower-detection
```

### 2. Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory based on the provided `.env.example`:
```bash
cp .env.example .env
```

Edit the `.env` file and add your Instagram credentials:
```
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```

Alternatively, you can use the secure credential storage system which will prompt you to set up encrypted credentials on first run.

### 5. Run the Application
```bash
python -m src.main
```

## Project Structure
```
├── data/                  # Data storage directory
├── logs/                  # Log files
├── credentials/           # Encrypted credentials storage
├── src/                   # Source code
│   ├── config/            # Configuration files
│   ├── data/              # Data processing modules
│   ├── models/            # Machine learning models
│   ├── scrapers/          # Web scraping modules
│   ├── utils/             # Utility functions
│   ├── visualization/     # Data visualization modules
│   └── main.py            # Main entry point
├── .env.example           # Example environment variables
├── .gitignore             # Git ignore file
├── README.md              # Project documentation
└── requirements.txt       # Python dependencies
```

## Complete Project Checklist

### Phase 1: Environment Setup and Dependencies
- [x] Create a virtual environment for the project
- [x] Install required Python packages:
  - [x] `selenium` for browser automation
  - [x] `undetected-chromedriver` for avoiding detection
  - [x] `beautifulsoup4` for HTML parsing
  - [x] `requests` for HTTP requests
  - [x] `pandas` for data manipulation
  - [x] `numpy` for numerical operations
  - [x] `scikit-learn` for machine learning algorithms
  - [x] `pytorch` for deep learning (if needed)
  - [x] `matplotlib` and `seaborn` for data visualization
  - [x] `streamlit` for dashboard creation (optional)
- [x] Set up a proper version control system (Git repository)
- [x] Create a comprehensive `.gitignore` file (include credentials and proxy lists)
- [x] Document environment setup in the README

### Phase 2: Web Scraping Infrastructure
- [x] Implement browser automation system:
  - [x] Configure undetected-chromedriver with proper settings
  - [x] Set up realistic user-agent rotation
  - [x] Implement cookie management system
  - [x] Create session persistence mechanism
- [x] Set up IP rotation and proxy management:
  - [x] Integrate proxy rotation system
  - [x] Implement IP ban detection and handling
  - [x] Create request throttling mechanism with random delays
- [x] Create error handling and retry mechanisms:
  - [x] Implement exponential backoff for failed requests
  - [x] Create logging system for debugging
  - [x] Set up automatic browser restart on detection
- [x] Develop anti-detection measures:
  - [x] Randomize mouse movements and scrolling behavior
  - [x] Implement realistic browsing patterns
  - [x] Add random pauses between actions

### Phase 3: Login Automation
- [x] Create secure credential storage system:
  - [x] Implement environment variable integration
  - [x] Set up encrypted credential storage
- [x] Develop Instagram login automation:
  - [x] Locate and interact with login form elements
  - [x] Handle two-factor authentication
  - [x] Implement CAPTCHA detection and manual intervention request
  - [x] Create session cookie management for future logins
- [x] Implement login verification:
  - [x] Check for successful login indicators
  - [x] Handle "suspicious login attempt" notifications
  - [x] Create credential rotation system (if using multiple accounts)

### Phase 4: Follower Data Collection
- [x] Develop follower list scraper:
  - [x] Navigate to profile and open followers list
  - [x] Implement infinite scroll to load all followers
  - [x] Extract follower usernames and metadata
  - [x] Store basic follower information (username, full name, bio, etc.)
- [x] Create follower profile analyzer:
  - [x] Navigate to individual follower profiles
  - [x] Extract profile statistics (posts count, followers, following)
  - [x] Identify account type (personal, business, creator)
  - [x] Determine account privacy status (public/private)
- [x] Implement follower categorization:
  - [x] Create preliminary classification based on profile metrics
  - [x] Flag potential bot accounts based on username patterns
  - [x] Document follower metadata in structured format

### Phase 5: Engagement Data Collection
- [ ] Create post interaction scraper:
  - [ ] Navigate to your recent posts
  - [ ] Extract like lists and compare against followers
  - [ ] Collect comment data and analyze commenter usernames
  - [ ] Track post view counts (if available)
- [ ] Implement story view analyzer:
  - [ ] Access story view lists from recent stories
  - [ ] Extract usernames from story viewers
  - [ ] Calculate story view rate for each follower
- [ ] Develop reel engagement tracker:
  - [ ] Navigate to recent reels
  - [ ] Collect like and comment data
  - [ ] Track reel view counts (if available)
- [ ] Create online activity monitor:
  - [ ] Detect "Active Now" status of followers
  - [ ] Track timing patterns of follower activity
  - [ ] Document last seen information when available

### Phase 6: Data Integration and Storage
- [ ] Design database schema:
  - [ ] Create tables for followers, posts, engagements
  - [ ] Define relationships between entities
  - [ ] Implement indexing for efficient queries
- [ ] Develop CSV export system:
  - [ ] Design normalized data structure
  - [ ] Implement automatic data export
  - [ ] Create data versioning mechanism
- [ ] Create incremental data collection:
  - [ ] Implement differential scraping to get only new data
  - [ ] Create data reconciliation mechanisms
  - [ ] Set up scheduled data collection jobs
- [ ] Implement data validation:
  - [ ] Create integrity checks for collected data
  - [ ] Develop data cleaning procedures
  - [ ] Implement error detection for scraping artifacts

### Phase 7: Data Preprocessing and Feature Engineering
- [ ] Clean and normalize raw data:
  - [ ] Handle missing values appropriately
  - [ ] Remove duplicates and inconsistencies
  - [ ] Standardize text fields and timestamps
- [ ] Create engagement features:
  - [ ] Calculate overall engagement rate per follower
  - [ ] Compute like ratio (likes/posts seen)
  - [ ] Determine comment frequency and depth
  - [ ] Measure story view consistency
- [ ] Develop temporal features:
  - [ ] Calculate recency of last engagement
  - [ ] Create time-based engagement decay metrics
  - [ ] Measure engagement consistency over time
  - [ ] Identify patterns in engagement timing
- [ ] Generate follower relationship features:
  - [ ] Analyze follower-to-following ratio
  - [ ] Calculate account age and maturity metrics
  - [ ] Determine content relevance scores
  - [ ] Identify common interests or hashtags

### Phase 8: Machine Learning Model Development
- [ ] Prepare labeled training data:
  - [ ] Create definition criteria for ghost followers
  - [ ] Manually label subset of followers for training
  - [ ] Implement stratified sampling for balanced dataset
  - [ ] Split data into training, validation, and test sets
- [ ] Implement feature selection:
  - [ ] Use correlation analysis to identify key features
  - [ ] Apply dimensionality reduction if needed
  - [ ] Normalize and scale features appropriately
- [ ] Train classification models:
  - [ ] Implement logistic regression baseline
  - [ ] Train random forest classifier
  - [ ] Develop gradient boosting model (XGBoost)
  - [ ] Create neural network classifier (PyTorch) if needed
- [ ] Evaluate and optimize models:
  - [ ] Implement cross-validation procedures
  - [ ] Calculate precision, recall, F1-score, and AUC
  - [ ] Perform hyperparameter optimization
  - [ ] Create ensemble methods for improved performance
- [ ] Handle special cases:
  - [ ] Develop mechanisms for handling class imbalance
  - [ ] Create separate models for different follower types
  - [ ] Implement confidence scores for predictions

### Phase 9: Ghost Follower Detection System
- [ ] Integrate the model into production:
  - [ ] Create model serialization and loading system
  - [ ] Implement batch prediction pipeline
  - [ ] Develop real-time prediction capabilities
- [ ] Create ghost follower categorization:
  - [ ] Classify ghosts by likelihood (definite/probable/possible)
  - [ ] Segment ghosts by account type and potential value
  - [ ] Identify likely bots versus inactive real users
- [ ] Implement exception handling:
  - [ ] Create whitelisting system for false positives
  - [ ] Develop verification procedures for borderline cases
  - [ ] Implement manual review queue for uncertain predictions
- [ ] Build prediction explanation system:
  - [ ] Generate reason codes for ghost classifications
  - [ ] Create feature importance visualization
  - [ ] Implement confidence scoring for predictions

### Phase 10: Reporting and Visualization
- [ ] Develop basic reporting system:
  - [ ] Create CSV exports of identified ghost followers
  - [ ] Generate summary statistics of follower engagement
  - [ ] Implement scheduled report generation
- [ ] Build interactive dashboard:
  - [ ] Create Streamlit web application
  - [ ] Implement interactive filters and sorts
  - [ ] Develop data visualization components
  - [ ] Create user-friendly interface for non-technical users
- [ ] Implement advanced analytics:
  - [ ] Track ghost follower trends over time
  - [ ] Analyze follower acquisition channels
  - [ ] Create engagement prediction for new followers
  - [ ] Develop follower quality scoring system

### Phase 11: System Automation
- [ ] Create scheduled execution system:
  - [ ] Implement cron jobs or task scheduler
  - [ ] Set up automatic data collection at optimal times
  - [ ] Create incremental processing of new data
- [ ] Develop monitoring and alerting:
  - [ ] Implement system health checks
  - [ ] Create alert system for scraping failures
  - [ ] Develop performance monitoring dashboard
- [ ] Implement error recovery:
  - [ ] Create automatic retry system for failed scrapes
  - [ ] Develop data backup and recovery procedures
  - [ ] Implement system state persistence

### Phase 12: Security and Compliance
- [ ] Enhance security measures:
  - [ ] Implement secure credential management
  - [ ] Create IP rotation and browser fingerprint randomization
  - [ ] Develop rate limiting and request throttling
- [ ] Create compliance documentation:
  - [ ] Document data handling procedures
  - [ ] Create privacy policy for collected data
  - [ ] Implement data retention and deletion protocols
- [ ] Develop ethical use guidelines:
  - [ ] Create documentation on proper usage
  - [ ] Implement safeguards against misuse
  - [ ] Develop user consent mechanisms

### Phase 13: Testing and Validation
- [ ] Create unit tests:
  - [ ] Test each scraping component individually
  - [ ] Validate data processing functions
  - [ ] Verify model prediction accuracy
- [ ] Implement integration tests:
  - [ ] Test end-to-end workflow
  - [ ] Validate system robustness
  - [ ] Measure performance under load
- [ ] Perform user acceptance testing:
  - [ ] Gather feedback from test users
  - [ ] Validate ghost follower identification accuracy
  - [ ] Test usability of reporting interface

### Phase 14: Documentation and Deployment
- [ ] Create comprehensive documentation:
  - [ ] Write technical system documentation
  - [ ] Develop user manual and guides
  - [ ] Document API if applicable
- [ ] Prepare deployment package:
  - [ ] Create Docker containers if needed
  - [ ] Develop installation scripts
  - [ ] Implement configuration management
- [ ] Create maintenance procedures:
  - [ ] Document update processes
  - [ ] Create troubleshooting guides
  - [ ] Develop system recovery procedures

## Technologies Used

- **Programming Language**: Python 3.9+
- **Web Scraping**: Selenium, BeautifulSoup, Requests
- **Data Processing**: Pandas, NumPy
- **Machine Learning**: Scikit-learn, PyTorch, XGBoost
- **Visualization**: Matplotlib, Seaborn, Plotly
- **Dashboard**: Streamlit
- **Storage**: CSV files, SQLite/PostgreSQL
- **Security**: Cryptography for credential encryption

## Secure Credential Storage

The system now includes a secure credential storage mechanism that:

1. Encrypts Instagram credentials using the cryptography library
2. Stores encrypted credentials on disk with a master password
3. Supports two-factor authentication
4. Handles suspicious login attempts
5. Manages session cookies for faster subsequent logins

On first run, you'll be prompted to:
- Enter your Instagram credentials
- Create a master password for encryption
- Specify if two-factor authentication is enabled

For subsequent runs, you'll only need to enter your master password to decrypt the stored credentials.

## Ethical Considerations

- Always respect Instagram's Terms of Service and consider legal alternatives
- Never automate the removal of followers (this can trigger account penalties)
- Secure all collected data and respect user privacy
- Consider obtaining explicit permission before collecting user data
- Use the system responsibly and for legitimate purposes only

## Future Enhancements

- Move from web scraping to Instagram's official API when possible
- Implement more sophisticated engagement metrics
- Add natural language processing for comment quality analysis
- Develop follower growth prediction models
- Create automated engagement strategy recommendations