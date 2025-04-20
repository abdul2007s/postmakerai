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
            Create a beautifully formatted English quiz for Telegram following this EXACT structure:

            1. Start with this exact title: <b>🇬🇧 ENGLISH QUIZ TIME! 🇬🇧</b>

            2. Then a short, engaging paragraph (2-3 sentences) explaining an interesting English concept. 
               Make this paragraph <i>visually appealing</i> with:
               • <b>Bold</b> for key terms
               • <i>Italics</i> for emphasis
               • <code>Monospace</code> for examples

            3. Then a clearly formatted question:
               <b>❓ [Your specific quiz question]</b>

            4. Three answer options with emojis:
               <b>❤️</b> [Option 1]
               <b>🥰</b> [Option 2]
               <b>👍</b> [Option 3]

            5. End with this exact line:
               <b>👇 Comment your answer below! 👇</b>

            Choose topics that include:
            • Grammar rules and usage
            • Vocabulary meanings and usage
            • Common phrases and idioms
            • Phrasal verbs
            • IELTS-related content
            • Speaking and writing tips

            Format guidelines:
            • Keep text clean and visually organized
            • Use spacing effectively
            • Make the quiz stand out visually
            • Keep entire quiz short and focused
            • No introductory phrases like "Here is" or "Today"

            At the very end, always include this exact text:
            "<b>Follow us:</b>
            <a href='https://t.me/ingliztiliuzz'>Telegram</a> | <a href='https://instagram.com/englishnativetv?igshid=ZDdkNTZiNTM='>Instagram</a> | <a href='https://m.youtube.com/@englishnativetv/videos'>YouTube</a>"
            """
        else:
            prompt = f"""
            Create a visually stunning English lesson about {topic} for Telegram.

            Structure the lesson in this format:

            1. Start with an eye-catching title:
               <b>📚 {topic.upper()} 📚</b>

            2. Immediately begin with the content - DO NOT use phrases like "Here is" or "Today we will learn"

            3. Format the lesson beautifully using these Telegram formatting options:
               • <b>Bold text</b> for all headings and important concepts
               • <i>Italic text</i> for examples and emphasis
               • <code>Monospace</code> for rules, formulas or things to remember
               • <u>Underline</u> for extra emphasis
               • ―――――――― (line separator) between sections
               • Emoji indicators at the start of each section (📝, 🔍, 💡, ✏️, etc.)

            4. Content must include:
               • Clear explanation of the concept
               • Examples with highlighted key elements
               • Common mistakes to avoid
               • Quick practice exercise
               • Key points to remember

            5. Visual Organization:
               • Use bullet points (•) and numbered lists
               • Create visual hierarchy with consistent styling
               • Add space between sections for readability
               • Use emoji as visual markers consistently (1-2 per section)
               • Keep paragraphs very short (1-2 sentences max)

            6. End with:
               💪 <b>Practice:</b> [One simple question or exercise]
               👇 <b>Reply with your answer in the comments!</b>

            Make it:
             • Direct and concise
             • Visually organized with clear sections
             • Educational but conversational
             • Easy to scan and read
             • Between 200-400 characters total

            At the very end, include this exact text:
            "<b>Follow us:</b>
           <a href='https://t.me/ingliztiliuzz'>Advanced English</a> | <a href='https://t.me/+T0wpLerxcpkudDo3'>Beginner English</a> | <a href='https://instagram.com/englishnativetv?igshid=ZDdkNTZiNTM='>Instagram</a> | <a href='https://m.youtube.com/@englishnativetv/videos'>YouTube</a>"
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
            
            # Post every 4 hours
            schedule.every(4).hours.do(post_with_rotating_topic)
            logger.info(f"Scheduled posts every 4 hours with rotating topics")
        else:
            # Random topics every 4 hours
            schedule.every(4).hours.do(self.post_daily_update)
            logger.info(f"Scheduled posts every 4 hours with random topics")
    
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
    TELEGRAM_BOT_TOKEN = "7990433756:AAGx4qxklD_CC9MTtIfGA5s7kBWgKzzIY54"  # Replace with your bot token from BotFather
    TELEGRAM_CHANNEL_ID = "@ingliztiliuzz"      # Replace with your channel username or ID
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
    
    # Schedule posts every 4 hours with English learning topics
    english_topics = [
        # Grammar & Vocabulary
        "English grammar tips for learners",
        "Common grammar mistakes in English",
        "Daily vocabulary words with meaning",
        "B1 vocabulary list with example sentences",
        "Useful English phrases for daily conversation",
        "Academic vs informal English vocabulary",
        
        # Phrases & Idioms
        "Most used English idioms with meanings",
        "Phrasal verbs list with examples",
        "English expressions for speaking fluently",
        "Everyday English phrases for beginners",
        "Slang vs idiom difference examples",
        
        # IELTS-Specific
        "IELTS writing task 1 and 2 tips",
        "IELTS speaking band 7 sample answers",
        "IELTS reading strategies for high score",
        "IELTS vocabulary for writing and speaking",
        "Common IELTS topics with sample answers",
        "IELTS academic vs general training difference",
        
        # Writing Skills
        "Connectors for IELTS writing",
        "Formal vs informal writing in English",
        "Common mistakes in English essays",
        
        # Speaking Skills
        "IELTS speaking part 1 sample questions",
        "Useful phrases for speaking fluently",
        "How to extend answers in speaking test",
        
        # Keep Quiz option for engagement
        "Quiz"
    ]
    
    # Post every 4 hours
    schedule.every(4).hours.do(lambda: manager.post_daily_update(random.choice(english_topics)))
    
    # Run the scheduler
    manager.run_scheduler()


# Run the bot
if __name__ == "__main__":
    # Install required packages:
    # pip install requests schedule
    main()