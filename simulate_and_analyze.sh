#!/bin/bash

# Default username
USERNAME="amaralkaff"

# Check if a username was provided
if [ $# -eq 1 ]; then
    USERNAME=$1
fi

echo "Running simulation and analysis for username: $USERNAME"

# Run the simulation and analysis
python -m src.main --simulate --analyze-engagement --target $USERNAME

echo "Simulation and analysis completed. Check the data directory for results." 