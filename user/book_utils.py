import requests
import random
from urllib.parse import quote

def search_books_by_mood_openlibrary(mood, limit=6):
    """
    Search for books based on user's mood using Open Library API
    Returns REAL books that exist on Open Library
    """
    # Mood to search terms mapping
    mood_search_terms = {
        'happy': ['happiness', 'joy', 'positive psychology', 'optimism'],
        'calm': ['mindfulness', 'meditation', 'peace', 'relaxation'],
        'stressed': ['stress relief', 'anxiety relief', 'calm', 'relaxation'],
        'anxious': ['anxiety relief', 'worry', 'fear', 'calm'],
        'motivated': ['motivation', 'success', 'productivity', 'goals'],
        'low': ['depression', 'hope', 'healing', 'recovery', 'inspiration'],
        'tired': ['rest', 'sleep', 'energy', 'wellness', 'recharge'],
        'energetic': ['exercise', 'fitness', 'energy', 'vitality'],
        'hopeful': ['hope', 'inspiration', 'courage', 'resilience'],
        'grateful': ['gratitude', 'appreciation', 'mindfulness'],
        'lonely': ['friendship', 'connection', 'community', 'belonging'],
        'peaceful': ['peace', 'serenity', 'quiet', 'stillness'],
        'loved': ['love', 'relationships', 'connection', 'heart'],
        'proud': ['achievement', 'success', 'accomplishment'],
        'excited': ['adventure', 'discovery', 'excitement'],
        'neutral': ['fiction', 'literature', 'classics', 'bestseller']
    }
    
    # Get search terms for the mood
    search_terms = mood_search_terms.get(mood, ['fiction', 'books'])
    search_term = random.choice(search_terms)
    
    try:
        # Open Library Search API
        url = f"http://openlibrary.org/search.json?q={quote(search_term)}&limit=20&fields=key,title,author_name,first_publish_year,ratings_average,ratings_count,cover_i,subject,ia"
        
        headers = {
            'User-Agent': 'EmpathyQ/1.0 (mental wellness app)'
        }
        
        response = requests.get(url, timeout=5, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            books = []
            
            if 'docs' in data and data['docs']:
                for doc in data['docs'][:limit]:
                    # Get cover image if available
                    cover_i = doc.get('cover_i')
                    cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg" if cover_i else None
                    
                    # Skip if no cover
                    if not cover_url:
                        continue
                    
                    # Get Open Library ID
                    olid = doc.get('key', '').replace('/works/', '')
                    if not olid:
                        continue
                    
                    # Get authors
                    authors = doc.get('author_name', ['Unknown Author'])
                    
                    # Get categories/subjects
                    subjects = doc.get('subject', ['General'])[:3]
                    
                    # Create book object with REAL Open Library links
                    book = {
                        'id': olid,
                        'title': doc.get('title', 'Unknown Title'),
                        'authors': authors,
                        'description': f"A book about {search_term} that matches your {mood} mood.",
                        'thumbnail': cover_url,
                        'preview_link': f"https://openlibrary.org/works/{olid}",
                        'info_link': f"https://openlibrary.org/works/{olid}",
                        'average_rating': doc.get('ratings_average', 4.0),
                        'ratings_count': doc.get('ratings_count', 1000),
                        'categories': subjects,
                        'recommendation_reason': get_recommendation_reason(mood)
                    }
                    
                    books.append(book)
                    
                    if len(books) >= limit:
                        break
                
                return books
        
        return []
        
    except Exception as e:
        print(f"Error fetching books: {e}")
        return []

def get_recommendation_reason(mood):
    """Generate a personalized reason for recommending this book"""
    
    reasons = {
        'happy': "This uplifting read will complement your positive mood",
        'excited': "Perfect for your adventurous spirit",
        'grateful': "A beautiful reminder of life's blessings",
        'hopeful': "Filled with inspiring stories to nurture your hope",
        'peaceful': "A calming read for your peaceful state of mind",
        'calm': "Gentle prose to maintain your tranquility",
        'loved': "Heartwarming stories about connection and love",
        'proud': "Celebrate achievements with this inspiring read",
        'motivated': "Fuel your motivation with this empowering book",
        'energetic': "Dynamic content matching your vibrant energy",
        'low': "A comforting companion during quiet moments",
        'tired': "Restorative reading for when you need to recharge",
        'stressed': "Soothing words to help you find balance",
        'anxious': "Grounding perspectives to ease your mind",
        'overwhelmed': "Simple wisdom to help you find clarity",
        'lonely': "Stories of connection to remind you you're not alone",
        'irritable': "Perspectives that foster understanding and patience",
        'confused': "Clarity and insight for your questioning mind",
        'hopeless': "Beacon of light to guide you forward",
        'neutral': "Engaging read for your balanced state",
    }
    
    return reasons.get(mood, "Perfectly matched to your current mood")

def get_mood_based_book_recommendations(mood, secondary_mood=None, limit=6):
    """
    Get REAL book recommendations from Open Library based on mood
    """
    # Try to get books from Open Library
    books = search_books_by_mood_openlibrary(mood, limit)
    
    # If we got books, return them
    if books:
        # Shuffle for variety
        random.shuffle(books)
        return books[:limit]
    
    # If no books found, try with secondary mood
    if secondary_mood:
        books = search_books_by_mood_openlibrary(secondary_mood, limit)
        if books:
            random.shuffle(books)
            return books[:limit]
    
    # Ultimate fallback - search for popular books
    books = search_books_by_mood_openlibrary('bestseller', limit)
    if books:
        return books[:limit]
    
    # If everything fails, return empty list
    return []

def get_books_with_unique_links(mood, secondary_mood=None, limit=6):
    """
    Get REAL book recommendations with working Open Library links
    """
    return get_mood_based_book_recommendations(mood, secondary_mood, limit)