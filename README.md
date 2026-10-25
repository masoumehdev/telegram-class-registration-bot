# Telegram Class Registration Bot

A Telegram bot for managing student registrations for educational classes.

## Features

- Class selection for grades 10, 11, and 12
- Student name and phone number collection
- Registration confirmation flow
- Phone number validation
- Prevention of duplicate registrations using a unique phone number constraint
- Class capacity management
- Payment record creation during registration
- Payment status tracking
- SQLite database integration
- Transaction-based registration and payment creation
- Rollback on database errors

## Technologies

- Python
- python-telegram-bot
- SQLite
- Git and GitHub

## Project Structure

- `bot.py` — Telegram bot handlers and conversation flow
- `database.py` — Database operations and registration/payment logic
- `test_set_payment.py` — Payment-related tests
- `.gitignore` — Excludes local databases, environment files, and Python-generated files

## Security

- Bot credentials are loaded from environment variables.
- Local database files and `.env` files are excluded from version control.

## Status

This project is under development.

## Author

GitHub: [@masoumehdev](https://github.com/masoumehdev)