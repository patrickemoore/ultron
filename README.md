# ultron

## Overview
Ultron is a multi-threaded system that leverages OpenAI's API to dynamically generate and execute code across multiple processes.

## Installation
- Ensure you have Python 3 installed.
- Install dependencies:
  ```
  pip install openai
  ```
- Set your OpenAI API key:
  ```
  export OPENAI_API_KEY=<your_api_key>
  ```

## Usage
- Run the application:
  ```
  python ultron.py
  ```
- The master process will spawn child processes that generate and display their interfaces.

## Contributing
Feel free to fork and submit pull requests.