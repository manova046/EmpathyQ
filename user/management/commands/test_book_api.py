from django.core.management.base import BaseCommand
from user.book_utils import search_books_by_mood, get_mood_based_book_recommendations

class Command(BaseCommand):
    help = 'Test book API for different moods'
    
    def add_arguments(self, parser):
        parser.add_argument('--mood', type=str, default='happy', help='Mood to test')
    
    def handle(self, *args, **options):
        mood = options['mood']
        
        self.stdout.write(f"Testing book API for mood: {mood}")
        
        # Test search_books_by_mood
        self.stdout.write("\n1. Testing search_books_by_mood...")
        books = search_books_by_mood(mood, limit=5)
        
        if books:
            self.stdout.write(self.style.SUCCESS(f"Found {len(books)} books:"))
            for i, book in enumerate(books, 1):
                self.stdout.write(f"  {i}. {book.get('title')} - {book.get('authors', ['Unknown'])[0]}")
        else:
            self.stdout.write(self.style.WARNING("No books found in search_books_by_mood"))
        
        # Test get_mood_based_book_recommendations
        self.stdout.write("\n2. Testing get_mood_based_book_recommendations...")
        recommendations = get_mood_based_book_recommendations(mood, limit=5)
        
        if recommendations:
            self.stdout.write(self.style.SUCCESS(f"Found {len(recommendations)} recommendations:"))
            for i, book in enumerate(recommendations, 1):
                self.stdout.write(f"  {i}. {book.get('title')} - Reason: {book.get('recommendation_reason')}")
        else:
            self.stdout.write(self.style.ERROR("No recommendations found!"))