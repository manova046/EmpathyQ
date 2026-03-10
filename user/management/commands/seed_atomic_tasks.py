# user/management/commands/seed_atomic_tasks.py
from django.core.management.base import BaseCommand
from django.utils import timezone

class Command(BaseCommand):
    help = 'Seed atomic tasks for emotional support'
    
    def handle(self, *args, **kwargs):
        # Import models
        try:
            from user.models import AtomicTask, TaskCategory
        except ImportError:
            self.stderr.write("Could not import models. Make sure:")
            self.stderr.write("1. 'user' is in INSTALLED_APPS")
            self.stderr.write("2. You're running from Django project root")
            return
        
        self.stdout.write("Creating atomic tasks...")
        
        # Clear existing data (optional)
        AtomicTask.objects.all().delete()
        TaskCategory.objects.all().delete()
        
        # Create categories
        categories = {
            'mindful': TaskCategory.objects.create(
                name='Mindfulness',
                description='Tasks to bring you into the present moment',
                icon='🧘'
            ),
            'movement': TaskCategory.objects.create(
                name='Movement',
                description='Gentle physical activities',
                icon='🚶'
            ),
            'creative': TaskCategory.objects.create(
                name='Creative',
                description='Expressive and creative tasks',
                icon='🎨'
            ),
            'selfcare': TaskCategory.objects.create(
                name='Self-Care',
                description='Nurturing activities for yourself',
                icon='💖'
            ),
            'connection': TaskCategory.objects.create(
                name='Connection',
                description='Activities involving others',
                icon='🤝'
            ),
            'grounding': TaskCategory.objects.create(
                name='Grounding',
                description='Tasks to help you feel centered',
                icon='🌍'
            ),
        }
        
        # Define atomic tasks for each mood
        atomic_tasks_data = [
            # For LOW mood
            {
                'title': '2-Minute Sunlight Break',
                'description': 'Step outside or near a window. Feel the sun on your skin for 2 minutes. Notice the temperature and light.',
                'mood': 'low',
                'category': categories['movement'],
                'duration_minutes': 2,
                'energy_level': 'low',
                'priority': 5,
            },
            {
                'title': 'Name 3 Gentle Things',
                'description': 'Look around and name 3 things that feel gentle or soft to you. Could be a blanket, a plant, or the light.',
                'mood': 'low',
                'category': categories['mindful'],
                'duration_minutes': 3,
                'energy_level': 'low',
                'priority': 4,
            },
            {
                'title': 'Sip Something Warm',
                'description': 'Make a warm drink. Hold the cup with both hands. Take slow sips, noticing the warmth and taste.',
                'mood': 'low',
                'category': categories['selfcare'],
                'duration_minutes': 5,
                'energy_level': 'low',
                'priority': 3,
            },
            
            # For ANXIOUS mood
            {
                'title': '5-4-3-2-1 Grounding',
                'description': 'Name: 5 things you see, 4 things you feel, 3 things you hear, 2 things you smell, 1 thing you taste.',
                'mood': 'anxious',
                'category': categories['grounding'],
                'duration_minutes': 3,
                'energy_level': 'medium',
                'priority': 5,
            },
            {
                'title': 'Box Breathing',
                'description': 'Breathe in for 4 counts, hold for 4 counts, exhale for 4 counts, hold for 4 counts. Repeat 5 times.',
                'mood': 'anxious',
                'category': categories['mindful'],
                'duration_minutes': 3,
                'energy_level': 'medium',
                'priority': 4,
            },
            {
                'title': 'Write Worries & Release',
                'description': 'Write down 3 worries on paper. Fold it up and put it away (physically or digitally). Say "I\'ll come back to this later."',
                'mood': 'anxious',
                'category': categories['creative'],
                'duration_minutes': 5,
                'energy_level': 'medium',
                'priority': 3,
            },
            
            # For STRESSED mood
            {
                'title': 'Desk Stretch Sequence',
                'description': 'Neck rolls, shoulder shrugs, wrist circles, seated forward fold. Hold each for 15 seconds.',
                'mood': 'stressed',
                'category': categories['movement'],
                'duration_minutes': 4,
                'energy_level': 'medium',
                'priority': 5,
            },
            {
                'title': 'Priority Check-In',
                'description': 'Ask: "What\'s the ONE most important thing I need to do next?" Write it down. Nothing else matters for 25 minutes.',
                'mood': 'stressed',
                'category': categories['selfcare'],
                'duration_minutes': 3,
                'energy_level': 'medium',
                'priority': 4,
            },
            {
                'title': 'Tense & Release',
                'description': 'Tense all muscles for 5 seconds, then completely release. Notice the difference. Repeat 3 times.',
                'mood': 'stressed',
                'category': categories['mindful'],
                'duration_minutes': 3,
                'energy_level': 'medium',
                'priority': 3,
            },
            
            # For CALM mood
            {
                'title': 'Gratitude Moment',
                'description': 'Write or think of 3 specific things you\'re grateful for right now. Be as detailed as possible.',
                'mood': 'calm',
                'category': categories['mindful'],
                'duration_minutes': 3,
                'energy_level': 'low',
                'priority': 4,
            },
            {
                'title': 'Gentle Intention Setting',
                'description': 'Close your eyes. Ask: "What quality would I like to cultivate in the next hour?" Examples: patience, creativity, focus.',
                'mood': 'calm',
                'category': categories['selfcare'],
                'duration_minutes': 2,
                'energy_level': 'low',
                'priority': 3,
            },
            {
                'title': 'Observe Nature',
                'description': 'Find something natural nearby (plant, cloud, insect). Observe it closely for 2 minutes without judgment.',
                'mood': 'calm',
                'category': categories['mindful'],
                'duration_minutes': 3,
                'energy_level': 'low',
                'priority': 2,
            },
            
            # For MOTIVATED mood
            {
                'title': 'Energizing Breath',
                'description': 'Take 5 quick, sharp inhales through nose, then one long exhale through mouth. Repeat 3 times.',
                'mood': 'motivated',
                'category': categories['movement'],
                'duration_minutes': 2,
                'energy_level': 'high',
                'priority': 5,
            },
            {
                'title': 'Power Pose',
                'description': 'Stand tall, hands on hips, feet shoulder-width. Hold for 2 minutes while breathing deeply.',
                'mood': 'motivated',
                'category': categories['movement'],
                'duration_minutes': 2,
                'energy_level': 'high',
                'priority': 4,
            },
            {
                'title': 'Quick Brain Dump',
                'description': 'Set timer for 3 minutes. Write ALL ideas/tasks on paper without editing or organizing.',
                'mood': 'motivated',
                'category': categories['creative'],
                'duration_minutes': 3,
                'energy_level': 'high',
                'priority': 3,
            },
            
            # For IRRITABLE mood
            {
                'title': 'Cool Water Break',
                'description': 'Splash cool water on face/wrists. Drink a glass of cold water slowly.',
                'mood': 'irritable',
                'category': categories['selfcare'],
                'duration_minutes': 3,
                'energy_level': 'medium',
                'priority': 5,
            },
            {
                'title': 'Boundary Visualization',
                'description': 'Imagine drawing a gentle circle of light around yourself. This is your space. Breathe into it.',
                'mood': 'irritable',
                'category': categories['mindful'],
                'duration_minutes': 2,
                'energy_level': 'medium',
                'priority': 4,
            },
            {
                'title': 'Physical Release',
                'description': 'Squeeze stress ball, shake out hands/arms vigorously for 30 seconds, then relax completely.',
                'mood': 'irritable',
                'category': categories['movement'],
                'duration_minutes': 2,
                'energy_level': 'high',
                'priority': 3,
            },
            
            # For NEUTRAL mood
            {
                'title': 'Mindful Posture Check',
                'description': 'Notice your posture. Adjust to sit/stand tall. Take 5 deep breaths in this aligned position.',
                'mood': 'neutral',
                'category': categories['mindful'],
                'duration_minutes': 2,
                'energy_level': 'medium',
                'priority': 3,
            },
            {
                'title': 'Micro-Connection',
                'description': 'Send a quick, genuine compliment or thank you to someone via text.',
                'mood': 'neutral',
                'category': categories['connection'],
                'duration_minutes': 3,
                'energy_level': 'medium',
                'priority': 2,
            },
        ]
        
        # Create all tasks
        tasks_created = 0
        for task_data in atomic_tasks_data:
            AtomicTask.objects.create(**task_data)
            tasks_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {TaskCategory.objects.count()} categories '
                f'and {tasks_created} atomic tasks!'
            )
        )