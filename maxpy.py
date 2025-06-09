import requests
import json
import time
import logging
import schedule
import random
import os
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PostMemory:
    """Class to store and track previously posted content to avoid repetition."""
    
    def __init__(self, memory_file="post_history_max.json"):
        """Initialize with a file to store post history."""
        self.memory_file = memory_file
        self.post_history = self._load_history()
        
    def _load_history(self):
        """Load post history from file or create if it doesn't exist."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    # Add topic_content if it doesn't exist in older files
                    if "topic_content" not in history:
                        history["topic_content"] = {}
                    return history
            except Exception as e:
                logger.error(f"Error loading post history: {e}")
                return {
                    "topics": {},
                    "content_hashes": [],
                    "quiz_topics": [],
                    "detailed_posts": [],
                    "topic_content": {}  # New: Track specific content per topic
                }
        else:
            return {
                "topics": {},
                "content_hashes": [],
                "quiz_topics": [],
                "detailed_posts": [],
                "topic_content": {}  # New: Track specific content per topic
            }
            
    def _save_history(self):
        """Save post history to file."""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.post_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving post history: {e}")
    
    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points or concepts from the content."""
        # Split content into sentences and clean them
        sentences = content.replace('<b>', '').replace('</b>', '')\
                         .replace('<i>', '').replace('</i>', '')\
                         .replace('\n', ' ').split('.')
        
        # Extract key points (sentences with important markers)
        key_points = []
        for sentence in sentences:
            sentence = sentence.strip()
            # Look for sentences that are likely key points
            if any(marker in sentence.lower() for marker in 
                  ['important', 'key', 'remember', 'note', 'tip', 'example',
                   'common mistake', 'correct way', 'incorrect', 'correct']):
                key_points.append(sentence)
            # Also include shorter, focused sentences
            elif 10 < len(sentence.split()) < 20:
                key_points.append(sentence)
                
        return key_points

    def is_content_similar(self, topic: str, new_content: str) -> bool:
        """Check if the new content is too similar to previously posted content for this topic."""
        if topic not in self.post_history["topic_content"]:
            return False
            
        new_key_points = set(self._extract_key_points(new_content))
        if not new_key_points:  # If no key points extracted, fall back to content hash
            return False
            
        # Check similarity with previous content
        for previous_points in self.post_history["topic_content"][topic]:
            previous_points_set = set(previous_points)
            # Calculate similarity using Jaccard similarity
            intersection = len(new_key_points.intersection(previous_points_set))
            union = len(new_key_points.union(previous_points_set))
            if union > 0 and intersection / union > 0.3:  # If more than 30% similar
                logger.warning(f"Content for topic '{topic}' is too similar to previous post")
                return True
                
        return False
    
    def record_post(self, topic: str, content: str):
        """Record a post to memory."""
        # Record topic usage
        if topic in self.post_history["topics"]:
            self.post_history["topics"][topic]["count"] += 1
            self.post_history["topics"][topic]["last_used"] = datetime.now().isoformat()
        else:
            self.post_history["topics"][topic] = {
                "count": 1,
                "last_used": datetime.now().isoformat()
            }
        
        # Record content hash
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        if content_hash not in self.post_history["content_hashes"]:
            self.post_history["content_hashes"].append(content_hash)
            if len(self.post_history["content_hashes"]) > 100:
                self.post_history["content_hashes"] = self.post_history["content_hashes"][-100:]
        
        # Record key points for this topic
        key_points = self._extract_key_points(content)
        if key_points:
            if topic not in self.post_history["topic_content"]:
                self.post_history["topic_content"][topic] = []
            self.post_history["topic_content"][topic].append(key_points)
            # Keep only last 10 sets of key points per topic
            if len(self.post_history["topic_content"][topic]) > 10:
                self.post_history["topic_content"][topic] = self.post_history["topic_content"][topic][-10:]
        
        # Store detailed post information
        post_summary = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "content_hash": content_hash,
            "key_points": key_points,
            "excerpt": content[:100] + "..." if len(content) > 100 else content
        }
        
        self.post_history["detailed_posts"].append(post_summary)
        if len(self.post_history["detailed_posts"]) > 30:
            self.post_history["detailed_posts"] = self.post_history["detailed_posts"][-30:]
        
        self._save_history()
    
    def is_content_duplicate(self, content: str) -> bool:
        """Check if content is too similar to previous posts."""
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        return content_hash in self.post_history["content_hashes"]
    
    def get_least_used_topics(self, topics: List[str], count: int = 10) -> List[str]:
        """Get topics that have been used least frequently."""
        topic_usage = []
        for topic in topics:
            if topic in self.post_history["topics"]:
                topic_usage.append((topic, self.post_history["topics"][topic]["count"]))
            else:
                topic_usage.append((topic, 0))
        
        topic_usage.sort(key=lambda x: x[1])
        return [t[0] for t in topic_usage[:count]]

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
            
            # Add explicit instruction to avoid introductory phrases
            prompt = "IMPORTANT: Do NOT include any introductory phrases like 'Here's', 'Here is', 'This is', etc. Start directly with the content.\n\n" + prompt
            
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
                
                # Remove common introductory phrases
                content = self._remove_introductory_phrases(content)
                
                return content
            else:
                logger.error(f"Error generating content: {response_data}")
                return ""
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return ""

    def _remove_introductory_phrases(self, content: str) -> str:
        """Remove common introductory phrases from the content."""
        introductory_phrases = [
            "Here's a Telegram lesson draft following your specifications:",
            "Here's a lesson draft:",
            "Here's the content:",
            "Here's a draft:",
            "Here's a Telegram post:",
            "Here is",
            "Here's",
            "This is",
            "I've created",
            "I have created",
            "Let me present",
            "Following your specifications:",
            "As requested:",
            "Draft:",
        ]
        
        # Remove phrases from the beginning of the content
        content = content.strip()
        lower_content = content.lower()
        
        for phrase in introductory_phrases:
            if lower_content.startswith(phrase.lower()):
                content = content[len(phrase):].strip()
                # Remove any leftover colons or newlines at the start
                content = content.lstrip(':\n').strip()
                
        return content

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
        self.memory = PostMemory()
        self.is_posting = False  # Lock to prevent multiple simultaneous posts
        logger.info("Automated Channel Manager initialized")
        
    def post_daily_update(self, topic: str = None):
        """Generate and post a daily update using Gemini AI."""
        if self.is_posting:
            logger.warning("Already generating a post, skipping this request")
            return False
            
        try:
            self.is_posting = True
            logger.info(f"Generating daily post{f' on {topic}' if topic else ''}")
            
            # Generate content
            post_data = self.gemini.generate_daily_post(topic)
            
            if not post_data or not post_data.get("content"):
                logger.error("Failed to generate content from Gemini API")
                return False
            
            # Check if content is duplicate
            if self.memory.is_content_duplicate(post_data["content"]):
                logger.warning("Generated duplicate content, skipping post")
                return False
            
            # Send to channel
            result = self.telegram.send_text_message(post_data["content"])
            
            if result and result.get('message_id'):
                logger.info(f"Daily post sent successfully: {post_data['title']}")
                
                # Record in memory
                self.memory.record_post(topic, post_data["content"])
                return True
            else:
                logger.error("Failed to send daily post")
                return False
                
        except Exception as e:
            logger.error(f"Error in post_daily_update: {e}")
            return False
        finally:
            self.is_posting = False
            
    def schedule_daily_posts(self, time_str: str = None, topics: List[str] = None):
        """Schedule posts at specified frequency with topic rotation."""
        # Clear any existing scheduled jobs
        schedule.clear()
        
        if topics:
            # Set up rotation through the provided topics, prioritizing least used ones
            def post_with_smart_topic_selection():
                if self.is_posting:
                    logger.warning("Post generation already in progress, skipping")
                    return
                    
                try:
                    # Get the 5 least used topics
                    least_used = self.memory.get_least_used_topics(topics, 5)
                    if least_used:
                        # Choose randomly from the least used topics
                        selected_topic = random.choice(least_used)
                        logger.info(f"Selected topic '{selected_topic}' from least used topics")
                        logger.info(f"Least used topics in queue: {', '.join(least_used)}")
                        
                        # Log topic history
                        recent_posts = self.memory.get_recent_posts(5)
                        if recent_posts:
                            logger.info("Recent post history:")
                            for post in recent_posts:
                                logger.info(f"- {post['topic']} (posted at {post['timestamp']})")
                        
                        return self.post_daily_update(selected_topic)
                    else:
                        # Fallback to random selection if history is empty
                        selected_topic = random.choice(topics)
                        logger.info(f"No history found, randomly selected topic: {selected_topic}")
                        return self.post_daily_update(selected_topic)
                except Exception as e:
                    logger.error(f"Error in post generation: {e}")
                    return False
            
            # Post every 6 hours
            schedule.every(6).hours.do(post_with_smart_topic_selection)
            logger.info("Post scheduling details:")
            logger.info(f"- Frequency: Every 6 hours")
            logger.info(f"- Total available topics: {len(topics)}")
            logger.info(f"- Topics in rotation: {', '.join(topics)}")
            logger.info("- Selection method: Smart rotation (prioritizing least used topics)")
        else:
            # Random topics every 6 hours
            schedule.every(6).hours.do(self.post_daily_update)
            logger.info("Post scheduling details:")
            logger.info("- Frequency: Every 6 hours")
            logger.info("- Selection method: Random topics")
    
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
    
    # English learning topics
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
    
    # Schedule posts using the method in AutomatedChannelManager
    manager.schedule_daily_posts(topics=english_topics)
    
    # Run the scheduler
    manager.run_scheduler()


# Run the bot
if __name__ == "__main__":
    # Install required packages:
    # pip install requests schedule
    main()