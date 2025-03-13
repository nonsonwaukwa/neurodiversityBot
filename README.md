# Odinma AI Accountability System

A WhatsApp-based AI accountability system that helps users manage tasks through AI-powered accountability and sentiment analysis.

## Features

- WhatsApp-based task management
- AI-powered sentiment analysis
- Dynamic task load adjustment
- Daily check-ins and reminders
- Admin dashboard for analytics
- Real-time data tracking

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   - Create a `.env` file with the following variables:
     ```
     FIREBASE_CREDENTIALS=path_to_firebase_credentials.json
     WHATSAPP_TOKEN=your_whatsapp_token
     DEEPSEEK_API_KEY=your_deepseek_api_key
     ```
4. Initialize Firebase:
   - Download your Firebase service account key
   - Place it in the `config` directory

## Project Structure

```
whatsapp_chatbot/
├── app/
│   ├── __init__.py
│   ├── routes/
│   ├── models/
│   ├── services/
│   └── utils/
├── config/
├── tests/
├── requirements.txt
└── README.md
```

## Running the Application

1. Start the Flask server:
   ```bash
   python run.py
   ```

2. The server will start on `http://localhost:5000`

## API Endpoints

- `POST /webhook`: WhatsApp webhook endpoint
- `GET /health`: Health check endpoint
- `POST /api/tasks`: Task management endpoint
- `GET /api/analytics`: Analytics endpoint

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 