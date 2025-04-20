import requests
import json
import time
import logging
import schedule
import random
from datetime import datetime
from typing import Optional, Dict, Any, List

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class GeminiAI:
    """Class to interact with Google's Gemini API."""
    
    def __init__(self, api_key: str):
        """Initialize with Gemini API key."""
        self.api_key = api_key
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        logger.info("Gemini AI initialized")
    
    def generate_content(self, prompt: str) -> str:
        """Generate content using Gemini AI."""
        try:
            url = f"{self.api_url}?key={self.api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response_data = response.json()
            
            if "candidates" in response_data and len(response_data["candidates"]) > 0:
                text_parts = []
                for part in response_data["candidates"][0]["content"]["parts"]:
                    if "text" in part:
                        text_parts.append(part["text"])
                content = ''.join(text_parts)
                
                # Remove Markdown formatting markers if they exist
                content = content.strip()
                if content.startswith("```html") or content.startswith("```"):
                    # Find the first closing ``` and remove everything before it
                    if "```" in content[3:]:
                        closing_index = content.find("```", 3)
                        if closing_index != -1:
                            content = content[closing_index + 3:].strip()
                    else:
                        # If no closing ```, just remove the opening markers
                        content = content.replace("```html", "", 1).replace("```", "", 1).strip()
                
                return content
            else:
                logger.error(f"Error generating content: {response_data}")
                return ""
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return ""
    
    def generate_daily_post(self, topic: str = None) -> Dict[str, str]:
        """Generate a complete daily post with title and content."""
        current_date = datetime.now().strftime("%B %d, %Y")
        
        if not topic:
            # Randomly select a topic if none provided
            topics = [
                "Quiz", "IELTS", "CEFR", "Vocabulary", "Speaking", "Fluent speaking", "Grammar"
            ]
            topic = random.choice(topics)
        
        if topic == "Quiz":
            prompt = f"""
            Create a simple, clear English quiz for Telegram (A1 level) following this EXACT structure:

            1. Start with this exact title: <b>🇬🇧 ENGLISH QUIZ TIME! 🇬🇧</b>

            2. Write a very short, simple explanation (2-3 short sentences) about a basic English concept. 
               Use only A1 level vocabulary and keep sentences under 6 words when possible.
               Format with:
               • <b>Bold</b> for important words
               • <i>Italic</i> for examples
               • <code>Monospace</code> for patterns

            3. Ask a very simple question:
               <b>❓ [Simple A1 level question]</b>

            4. Provide three easy answer options:
               <b>❤️</b> [Simple Option 1]
               <b>🥰</b> [Simple Option 2]
               <b>👍</b> [Simple Option 3]

            5. End with:
               <b>👇 Comment your answer below! 👇</b>

            Quiz should test only basic A1 level concepts:
            • Simple present tense (I eat)
            • Basic verbs (go, come, have)
            • Numbers 1-20
            • Colors and basic objects
            • Common adjectives (big, small)
            • Family words (mother, father)
            • Simple greetings (hello, goodbye)
            • Days of the week
            • Basic question words (what, where)

            Make the quiz:
            • Simple and clear
            • Visually well-organized
            • Focused on one basic concept
            • Encouraging for learners
            • Free of complex vocabulary

            At the very end, always include this exact text:
            "<b>Follow us:</b>
            <a href='https://t.me/ingliztiliuzz'>Advanced English</a> | <a href='https://t.me/+T0wpLerxcpkudDo3'>Beginner English</a> | <a href='https://instagram.com/englishnativetv?igshid=ZDdkNTZiNTM='>Instagram</a> | <a href='https://m.youtube.com/@englishnativetv/videos'>YouTube</a>"
            """
        else:
            prompt = f"""
            Create a clear, simple English lesson about {topic} for Telegram (A1 level). Make it educational and easy to understand.

            Structure the lesson in this format:

            1. Start with a simple title:
               <b>📚 ENGLISH: {topic.upper()} 📚</b>

            2. Include a very short introduction (1 sentence only) that explains what students will learn

            3. TEACH the concept step-by-step:
               • Start with the most basic explanation possible
               • Use <b>bold</b> for important words
               • Use <i>italics</i> for examples
               • Use <code>monospace</code> for rules or patterns
               • Include 3-4 VERY SIMPLE examples
               • Show the pattern or structure clearly

            4. Format the content using:
               • Short, simple sentences (max 8 words per sentence)
               • Visual separation between points (――――)
               • Simple vocabulary only (A1 level)
               • Numbered steps when explaining rules
               • Emoji indicators for different sections (📝, 🔍, 💡)
               • Images using emoji if helpful

            5. Include a PRACTICAL LESSON with:
               • 2-3 extremely simple example sentences
               • Fill-in-the-blank exercises
               • Multiple choice practice
               • Example dialogues (for conversation topics)
               • Visual aid with emoji or formatting

            6. End with:
               💪 <b>Practice:</b> [One very simple exercise]
               👇 <b>Write your answer in the comments!</b>

            Important guidelines:
             • Use ONLY A1 level vocabulary
             • Make sentences extremely simple and short
             • Explain every new word or concept
             • Use repetition to reinforce learning
             • Be encouraging and positive
             • Total content should be 300-400 characters

            At the very end, include this exact text:
            "<b>Follow us:</b>
            <a href='https://t.me/ingliztiliuzz'>Telegram</a> | <a href='https://instagram.com/englishnativetv?igshid=ZDdkNTZiNTM='>Instagram</a> | <a href='https://m.youtube.com/@englishnativetv/videos'>YouTube</a>"
            """
        
        content = self.generate_content(prompt)
        
        # Extract title if possible
        title = "English Learning"
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith('#'):
                title = line.strip().lstrip('#').strip()
                break
                
        return {
            "title": title,
            "content": content
        }


class TelegramChannelAdmin:
    """A class to manage and send posts to a Telegram channel using direct API calls."""
    
    def __init__(self, token: str, channel_id: str):
        """Initialize with bot token and channel ID."""
        self.token = token
        self.channel_id = channel_id
        self.api_url = f"https://api.telegram.org/bot{token}"
        logger.info(f"Bot initialized for channel: {channel_id}")
    
    def _make_request(self, method: str, params: Dict[str, Any]) -> Dict:
        """Make a request to the Telegram Bot API."""
        url = f"{self.api_url}/{method}"
        try:
            response = requests.post(url, params)
            response_data = response.json()
            
            if not response_data.get('ok'):
                logger.error(f"API error: {response_data.get('description')}")
                return {}
                
            return response_data.get('result', {})
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {}
    
    def get_channel_info(self) -> Dict:
        """Get information about the channel."""
        result = self._make_request("getChat", {"chat_id": self.channel_id})
        
        if result:
            # Try to get member count in a separate request
            member_count_result = self._make_request("getChatMemberCount", {"chat_id": self.channel_id})
            member_count = member_count_result if member_count_result else "Unknown"
            
            return {
                'id': result.get('id'),
                'title': result.get('title'),
                'description': result.get('description'),
                'member_count': member_count
            }
        return {}
    
    def send_text_message(self, text: str, disable_notification: bool = False) -> Dict:
        """Send a text message to the channel."""
        params = {
            "chat_id": self.channel_id,
            "text": text,
            "disable_notification": disable_notification,
            "parse_mode": "HTML",  # Enable HTML formatting
            "disable_web_page_preview": True  # Disable link previews
        }
        result = self._make_request("sendMessage", params)
        
        if result:
            logger.info(f"Message sent with ID: {result.get('message_id')}")
        
        return result
    
    def send_photo(self, photo_path: str, caption: Optional[str] = None, 
                  disable_notification: bool = False) -> Dict:
        """Send a photo to the channel."""
        try:
            with open(photo_path, 'rb') as photo_file:
                url = f"{self.api_url}/sendPhoto"
                files = {"photo": photo_file}
                data = {
                    "chat_id": self.channel_id,
                    "disable_notification": disable_notification,
                    "parse_mode": "HTML"  # Enable HTML formatting
                }
                
                if caption:
                    data["caption"] = caption
                
                response = requests.post(url, data=data, files=files)
                response_data = response.json()
                
                if not response_data.get('ok'):
                    logger.error(f"API error: {response_data.get('description')}")
                    return {}
                    
                result = response_data.get('result', {})
                if result:
                    logger.info(f"Photo sent with ID: {result.get('message_id')}")
                
                return result
        except FileNotFoundError:
            logger.error(f"Photo file not found: {photo_path}")
            return {}
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return {}
    
    def delete_message(self, message_id: int) -> bool:
        """Delete a message from the channel."""
        params = {
            "chat_id": self.channel_id,
            "message_id": message_id
        }
        result = self._make_request("deleteMessage", params)
        
        if result or result == True:  # deleteMessage returns True on success
            logger.info(f"Message deleted: {message_id}")
            return True
        
        return False
    
    def pin_message(self, message_id: int, disable_notification: bool = False) -> bool:
        """Pin a message in the channel."""
        params = {
            "chat_id": self.channel_id,
            "message_id": message_id,
            "disable_notification": disable_notification
        }
        result = self._make_request("pinChatMessage", params)
        
        if result or result == True:  # pinChatMessage returns True on success
            logger.info(f"Message pinned: {message_id}")
            return True
        
        return False


class AutomatedChannelManager:
    """Class to manage automated posting to a Telegram channel using Gemini AI."""
    
    def __init__(self, telegram_token: str, telegram_channel_id: str, gemini_api_key: str):
        """Initialize with required API tokens and channel ID."""
        self.telegram = TelegramChannelAdmin(telegram_token, telegram_channel_id)
        self.gemini = GeminiAI(gemini_api_key)
        logger.info("Automated Channel Manager initialized")
        
    def post_daily_update(self, topic: str = None):
        """Generate and post a daily update using Gemini AI."""
        logger.info(f"Generating daily post{f' on {topic}' if topic else ''}")
        
        try:
            # Generate content
            post_data = self.gemini.generate_daily_post(topic)
            
            if not post_data or not post_data.get("content"):
                logger.error("Failed to generate content from Gemini API")
                return False
                
            # Send to channel
            result = self.telegram.send_text_message(post_data["content"])
            
            if result and result.get('message_id'):
                logger.info(f"Daily post sent successfully: {post_data['title']}")
                return True
            else:
                logger.error("Failed to send daily post")
                return False
        except Exception as e:
            logger.error(f"Error in post_daily_update: {e}")
            return False

    def schedule_daily_posts(self, time_str: str = None, topics: List[str] = None):
        """Schedule posts at specified frequency with topic rotation."""
        if topics:
            # Set up rotation through the provided topics
            topic_index = 0
            
            def post_with_rotating_topic():
                nonlocal topic_index
                current_topic = topics[topic_index]
                self.post_daily_update(current_topic)
                topic_index = (topic_index + 1) % len(topics)
            
            # Post every minute for testing
            schedule.every(1).minutes.do(post_with_rotating_topic)
            logger.info(f"Scheduled posts every minute with rotating topics")
        else:
            # Random topics every minute
            schedule.every(1).minutes.do(self.post_daily_update)
            logger.info(f"Scheduled posts every minute with random topics")
    
    def run_scheduler(self):
        """Run the scheduler loop."""
        logger.info("Starting scheduler. Press Ctrl+C to exit.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  
        except KeyboardInterrupt:
            logger.info("Scheduler stopped.")


# Main function to run the bot
def main():
    # Configure your API keys and channel ID directly here
    TELEGRAM_BOT_TOKEN = "7724049750:AAHSYv5KSn3etGhH8BmteY3YtsbCOWmGgsQ"  # Replace with your bot token from BotFather
    TELEGRAM_CHANNEL_ID = "@max_english"      # Replace with your channel username or ID
    GEMINI_API_KEY = "AIzaSyDvcXsBl_zYBQzsKLoZJ6Tm09JGfCOMGYM"          # Replace with your Gemini API key
    
    # Initialize automated channel manager
    manager = AutomatedChannelManager(
        telegram_token=TELEGRAM_BOT_TOKEN,
        telegram_channel_id=TELEGRAM_CHANNEL_ID,
        gemini_api_key=GEMINI_API_KEY
    )
    
    # Post immediately as a test
    print("Testing post generation...")
    success = manager.post_daily_update("Quiz")
    print(f"Post test result: {'Success' if success else 'Failed'}")
    
    if not success:
        print("Testing direct API calls...")
        # Test Gemini API directly
        gemini = GeminiAI(GEMINI_API_KEY)
        test_content = gemini.generate_content("Generate a short English quiz question with 3 possible answers.")
        print(f"Gemini API test result: {'Success' if test_content else 'Failed'}")
        if test_content:
            print("Content sample:", test_content[:100] + "...")
            
        # Test Telegram API directly
        telegram = TelegramChannelAdmin(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)
        test_message = telegram.send_text_message("This is a test message from our English learning bot.")
        print(f"Telegram API test result: {'Success' if test_message else 'Failed'}")
    
    # Schedule posts every minute with English learning topics
    english_topics = [
        # A1 Grammar Topics
        "To be verb A1 level",
        "Present simple A1 grammar",
        "Articles (a/an/the) for beginners",
        "Beginner English pronouns",
        "Possessive adjectives (my, your, his)",
        "Simple questions in English",
        "Basic sentence structure",
        "Singular and plural nouns",
        "A1 level prepositions",
        "This/That/These/Those",
        
        # A1 Vocabulary Topics
        "Daily routine vocabulary A1",
        "Clothes vocabulary beginner",
        "Food and drinks vocabulary A1", 
        "Family members vocabulary",
        "Colors and shapes vocabulary",
        "Numbers and counting in English",
        "Days of the week and months",
        "Common adjectives for beginners",
        "Basic action verbs A1 level",
        "Weather vocabulary A1",
        
        # A1 Level Phrases
        "Greetings and introductions A1",
        "Asking for directions simply",
        "Ordering food and drinks",
        "Simple telephone conversations",
        "Shopping phrases for beginners",
        "Telling the time A1 level",
        "Asking simple questions",
        "Describing yourself A1",
        "Making simple requests",
        "Basic classroom English",
        
        # Quiz for engagement
        "Quiz"
    ]
    
    # Post every minute for testing
    schedule.every(1).minutes.do(lambda: manager.post_daily_update(random.choice(english_topics)))
    
    # Run the scheduler
    manager.run_scheduler()


# Run the bot
if __name__ == "__main__":
    # Install required packages:
    # pip install requests schedule
    main()