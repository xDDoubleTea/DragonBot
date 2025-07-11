# Dragon Bot

![Bot Status](https://img.shields.io/badge/status-active-success)

Dragon Bot is a multi-purpose Discord bot designed with a primary focus on providing a robust and user-friendly ticket management system. This project is a complete, from-scratch rewrite of the original `DragonBot_host` repository, built with modern `discord.py` features, a scalable architecture, and a strong emphasis on developer and user experience.

This project reflects my journey in software design, moving from a monolithic script to a structured, maintainable application.

## Key Features

- 🎟️ **Ticket System:** A comprehensive ticket management system allowing users to create, manage, and close support tickets through dedicated channels.
- 👑 **Role Requesting System:** A configurable system for users to request roles, with an approval workflow for administrators.
- 🔑 **Keyword System:** An automated response system that replies to user-defined keywords and triggers.
- ...and more utilities designed to improve server management (To be added).

## Setup & Installation (Self-Hosting)

This guide is for developers who wish to self-host the bot.

> Note: I am using Arch linux myself, so if you are using a different OS, some commands may vary slightly. If you encounter issues, please open an issue on the GitHub repository.

1. **Clone the repository**

    ```bash
    git clone https://github.com/xDDoubleTea/DragonBot.git
    cd DragonBot
    ```

2. **Create and activate a virtual environment**

    Prefered using [astral-sh/uv: An extremely fast Python package and project manager, written in Rust.](https://github.com/astral-sh/uv/tree/main), the python virtual environment manager, but you can use any virtual environment tool you prefer.
    After git cloning, run the following commands to set up the virtual environment:

    ```bash
    uv sync
    source .venv/bin/activate
    ```

    Or, if you are using vscode, you have to select the virtual environment as your interpreter.
    If you are using a different virtual environment tool, the command may vary. For example, if you are using `venv`, you can run:

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

    If you are using `virtualenv`, you can run:

    ```bash
    virtualenv .venv
    source .venv/bin/activate
    ```

3. **Install dependencies**
    If you are using `uv`, then the `uv sync` command will automatically install the dependencies for you. If you are using a different virtual environment tool, you can run the following command to install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. **Configure the environment**
    Copy the example environment file. This file contains all the necessary environment variables you need to configure.

    ```bash
    cp .env.example .env
    ```

    Next, edit the `.env` file with your own values, including your bot token and database URL.
    **Remember to change the configuration in `config/` to match your server's configuration, such as the guild ID, support role ID, and other settings. Or the bot won't work**

5. **Run the bot**

    ```bash
    python main.py
    ```

    Please ensure that you have the necessary permissions to run the bot in your Discord server, and that you have invited the bot with the correct scopes and permissions.

## Technology Stack

- **Language:** Python 3.10+
- **Core Library:** `discord.py`
- **Database:** PostgreSQL with `asyncpg`
- **ORM:** SQLAlchemy
- **Documentation:** MkDocs

## Contributing

Fork the repository, create a new branch, and submit a pull request. Contributions are welcome!  
Recommend to read the [contribution guide](CONTRIBUTING.md) for more details. You can also first open an issue to discuss your changes.  
