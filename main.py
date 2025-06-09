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
    
    def __init__(self, memory_file="post_history.json"):
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
            "key_points": key_points,  # Add key points to summary
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
        # Create list of (topic, usage_count) pairs
        topic_usage = []
        for topic in topics:
            if topic in self.post_history["topics"]:
                # If topic exists in history, get its usage count
                topic_usage.append((topic, self.post_history["topics"][topic]["count"]))
            else:
                # If topic has never been used, count is 0
                topic_usage.append((topic, 0))
        
        # Sort by usage count (least used first)
        topic_usage.sort(key=lambda x: x[1])
        # Return just the topic names, limited to requested count
        return [t[0] for t in topic_usage[:count]]
        
    def is_quiz_topic_used(self, topic: str) -> bool:
        """Check if a specific quiz topic has been used before."""
        return topic in self.post_history["quiz_topics"]
    
    def get_recent_posts(self, count: int = 5) -> List[Dict]:
        """Get the most recent posts for analysis."""
        return self.post_history["detailed_posts"][-count:] if "detailed_posts" in self.post_history else []

class GeminiAI:
    """Class to interact with Google's Gemini API."""
    
    def __init__(self, api_key: str):
        """Initialize with Gemini API key."""
        self.api_key = api_key
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        self.previous_quiz_topics = []  # Track previously used quiz topics
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
        
        # Simplified topic-specific emoji mappings (just 2 primary emojis per topic)
        topic_emojis = {
            "Grammar": ["📝", "✍️"],
            "IELTS": ["🎓", "📚"],
            "CEFR": ["🌍", "📊"],
            "Vocabulary": ["📚", "💡"],
            "Speaking": ["🗣️", "🎯"],
            "Fluent speaking": ["🗣️", "⭐"],
            "Pronunciation": ["🗣️", "🎵"],
            "Writing": ["✍️", "📝"],
            "Reading": ["📖", "👀"],
            "Listening": ["👂", "🎧"],
            "Idioms": ["💭", "💡"],
            "Phrasal Verbs": ["📚", "💫"],
            "Business English": ["💼", "📊"],
            "Academic English": ["🎓", "📚"],
            "Common Mistakes": ["⚠️", "✅"],
            "Daily Conversation": ["💬", "👥"],
            "Exam Tips": ["📝", "✅"]
        }

        if not topic:
            topics = list(topic_emojis.keys()) + ["Quiz"]
            topic = random.choice(topics)
        
        if topic == "Quiz":
            # Quiz format remains the same for consistency
            avoided_topics = ""
            if self.previous_quiz_topics:
                avoided_topics = f"""
                IMPORTANT: Please avoid creating quizzes about these previously used topics:
                {', '.join(self.previous_quiz_topics[-15:])}.
                Choose a completely different quiz topic.
                """
                
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

            {avoided_topics}
            
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

            At the very end, include this exact text:
            "<b>Follow us:</b>
            <a href='https://t.me/ingliztiliuzz'>Telegram</a> | <a href='https://instagram.com/englishnativetv?igshid=ZDdkNTZiNTM='>Instagram</a> | <a href='https://m.youtube.com/@englishnativetv/videos'>YouTube</a>"
            """
        else:
            # Get topic-specific emojis
            topic_specific_emojis = topic_emojis.get(topic, ["📚", "💡"])
            
            # Different template styles for regular posts
            templates = [
                # Style 1: Did You Know Format
                f"""
                Create a clean, simple English lesson about {topic} for Telegram.

                First, analyze the topic and select ONE most appropriate emoji that represents this topic perfectly.
                Consider the context, meaning, and purpose of the lesson. The emoji should be intuitive and help users 
                quickly understand what the lesson is about.

                Structure:
                1. Title:
                    • Choose ONE perfect emoji for this topic
                    • Format as: <b>[chosen_emoji] {topic.upper()}</b>
                    • The emoji must be relevant and meaningful

                2. Content:
                    • Start with a short, engaging introduction
                    • Explain the concept clearly
                    • Include 1-2 practical examples
                    • Use <b>bold</b> for key terms (max 2)
                    • Use <i>italic</i> for examples
                    • Keep paragraphs short and focused

                3. Key Points:
                    • List 2-3 main takeaways
                    • Keep each point clear and memorable
                    • Use bullet points for organization

                Guidelines:
                • Write in a friendly, conversational tone
                • Keep it simple and readable
                • Total length: 300-400 characters
                • Make it practical and useful
                • Use natural spacing for readability

                At the very end, include this exact text:
                "<b>Follow us:</b>
                <a href='https://t.me/ingliztiliuzz'>Advanced English</a> | <a href='https://t.me/+T0wpLerxcpkudDo3'>Beginner English</a> | <a href='https://instagram.com/englishnativetv?igshid=ZDdkNTZiNTM='>Instagram</a> | <a href='https://m.youtube.com/@englishnativetv/videos'>YouTube</a>"
                """
            ]
            
            # Select a random template
            prompt = random.choice(templates) + """
            At the very end, include this exact text:
            "<b>Follow us:</b>
            <a href='https://t.me/ingliztiliuzz'>Advanced English</a> | <a href='https://t.me/+T0wpLerxcpkudDo3'>Beginner English</a> | <a href='https://instagram.com/englishnativetv?igshid=ZDdkNTZiNTM='>Instagram</a> | <a href='https://m.youtube.com/@englishnativetv/videos'>YouTube</a>"
            """
        
        content = self.generate_content(prompt)
        
        # Extract title and quiz topic
        title = "English Learning"
        quiz_topic = ""
        
        if topic == "Quiz":
            # Try to extract the quiz topic using several methods
            lines = content.split('\n')
            
            # Method 1: Look for the question line (with ❓)
            for line in lines:
                if "❓" in line:
                    question_text = line.replace("❓", "").replace("<b>", "").replace("</b>", "").strip()
                    # Extract core topic from question
                    quiz_topic = self._extract_quiz_topic_from_question(question_text)
                    break
            
            # Method 2: If method 1 failed, look for bold text in the explanation paragraph
            if not quiz_topic:
                for line in lines:
                    if "<b>" in line and "</b>" in line and not "ENGLISH QUIZ TIME" in line:
                        # Extract the bold terms as they likely represent the topic
                        bold_parts = []
                        start_idx = 0
                        while "<b>" in line[start_idx:]:
                            b_start = line.find("<b>", start_idx)
                            b_end = line.find("</b>", b_start)
                            if b_start != -1 and b_end != -1:
                                bold_parts.append(line[b_start+3:b_end].strip())
                                start_idx = b_end + 4
                            else:
                                break
                        
                        if bold_parts:
                            quiz_topic = ", ".join(bold_parts)
                            break
            
            # Method 3: Just use the first paragraph if all else fails
            if not quiz_topic:
                for line in lines:
                    if line.strip() and not "ENGLISH QUIZ TIME" in line:
                        words = line.split()
                        quiz_topic = " ".join(words[:min(5, len(words))])
                        break
            
            # Store the quiz topic to avoid repetition
            if quiz_topic and quiz_topic not in self.previous_quiz_topics:
                self.previous_quiz_topics.append(quiz_topic)
                # Keep only the most recent 30 topics
                if len(self.previous_quiz_topics) > 30:
                    self.previous_quiz_topics = self.previous_quiz_topics[-30:]
            
            logger.info(f"Extracted quiz topic: {quiz_topic}")
                
        else:
            # For non-quiz posts, just extract title from first line
            lines = content.split('\n')
            for line in lines:
                if line.strip().startswith('#'):
                    title = line.strip().lstrip('#').strip()
                    break
                
        return {
            "title": title,
            "content": content,
            "quiz_topic": quiz_topic if topic == "Quiz" else None
        }
    
    def _extract_quiz_topic_from_question(self, question: str) -> str:
        """Extract the core topic from a quiz question."""
        # Remove common question starters
        starters = [
            "What is", "What are", "Which of", "How do", "How does", "When should", 
            "Can you", "Where is", "Who is", "Why is", "What does", "How many"
        ]
        
        for starter in starters:
            if question.startswith(starter):
                question = question.replace(starter, "", 1).strip()
                break
        
        # Extract meaningful parts (first 5-7 words)
        words = question.split()
        if len(words) <= 7:
            return question
        else:
            # Take the first 5-7 words that likely represent the topic
            return " ".join(words[:min(7, len(words))])


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
                
                # For quiz posts, store the specific quiz topic instead of just "Quiz"
                memory_topic = topic
                if topic == "Quiz" and post_data.get("quiz_topic"):
                    quiz_topic = post_data["quiz_topic"]
                    memory_topic = f"Quiz: {quiz_topic}"
                    logger.info(f"Recording specific quiz topic: {memory_topic}")
                
                # Record in memory with the specific topic
                self.memory.record_post(memory_topic, post_data["content"])
                return True
            else:
                logger.error("Failed to send daily post")
                return False
                
        except Exception as e:
            logger.error(f"Error in post_daily_update: {e}")
            return False
        finally:
            self.is_posting = False  # Release the lock
            
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
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user.")
            schedule.clear()  # Clear all scheduled jobs
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            schedule.clear()  # Clear all scheduled jobs


# Main function to run the bot
def main():
    # Configure your API keys and channel ID directly here
    TELEGRAM_BOT_TOKEN = "7990433756:AAGx4qxklD_CC9MTtIfGA5s7kBWgKzzIY54"  # Replace with your bot token from BotFather
    TELEGRAM_CHANNEL_ID = "@Ingliztiliuzz"      # Replace with your channel username or ID
    GEMINI_API_KEY = "AIzaSyDvcXsBl_zYBQzsKLoZJ6Tm09JGfCOMGYM"          # Replace with your Gemini API key
    
    # Initialize automated channel manager
    manager = AutomatedChannelManager(
        telegram_token=TELEGRAM_BOT_TOKEN,
        telegram_channel_id=TELEGRAM_CHANNEL_ID,
        gemini_api_key=GEMINI_API_KEY
    )
    
    # English learning topics
    english_topics = [
        # Advanced Topics
        "Advanced Grammar Structure",
        "Advanced Vocabulary",
        
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
    
    # Schedule posts with smart topic selection
    manager.schedule_daily_posts(topics=english_topics)
    
    print("Bot started. Press Ctrl+C to exit.")
    try:
        # Run the scheduler
        manager.run_scheduler()
    except KeyboardInterrupt:
        print("Bot stopped by user.")
    except Exception as e:
        print(f"Error: {e}")
        
if __name__ == "__main__":
    main()