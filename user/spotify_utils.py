import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from django.conf import settings
import random

# Mood to Spotify genre/playlist mapping
MOOD_PLAYLISTS = {
    'happy': [
        'spotify:playlist:37i9dQZF1DXdPec7aLTmlC',  # Happy Hits
        'spotify:playlist:37i9dQZF1DX3rxVfibe1L0',  # Mood Booster
        'spotify:playlist:37i9dQZF1DX9XIFQuFvzM4',  # Feelin' Good
    ],
    'excited': [
        'spotify:playlist:37i9dQZF1DX0XUsuxWHRQd',  # RapCaviar
        'spotify:playlist:37i9dQZF1DX76Wlfdnj7AP',  # Beast Mode
        'spotify:playlist:37i9dQZF1DX0BcQWzuB7ZO',  # Happy Beats
    ],
    'grateful': [
        'spotify:playlist:37i9dQZF1DWXRqgorJj26U',  # Gratitude
        'spotify:playlist:37i9dQZF1DX0XUsuxWHRQd',  # Chill Vibes
        'spotify:playlist:37i9dQZF1DXcBWIGoYBM5M',  # Today's Top Hits
    ],
    'hopeful': [
        'spotify:playlist:37i9dQZF1DX0s5kDXi1oC5',  # Hope
        'spotify:playlist:37i9dQZF1DX7qK8ma5wgG1',  # inspirational
        'spotify:playlist:37i9dQZF1DX2sUQwD7tbmL',  # Feel Good
    ],
    'peaceful': [
        'spotify:playlist:37i9dQZF1DWZqd5JICZI0u',  # Peace
        'spotify:playlist:37i9dQZF1DWY4lFlS4Pnso',  # Calm Vibes
        'spotify:playlist:37i9dQZF1DX3Ogo9pFvBkY',  # Ambient Relaxation
    ],
    'calm': [
        'spotify:playlist:37i9dQZF1DX3Ogo9pFvBkY',  # Ambient Relaxation
        'spotify:playlist:37i9dQZF1DX3Ogo9pFvBkY',  # Peaceful Piano
        'spotify:playlist:37i9dQZF1DX4WYpdgoIcn6',  # Chill Hits
    ],
    'loved': [
        'spotify:playlist:37i9dQZF1DXbwjaKZ52TPQ',  # Love
        'spotify:playlist:37i9dQZF1DX7K31D69s4M1',  # Romantic
        'spotify:playlist:37i9dQZF1DXbm6HfkbMtFZ',  # Soft Pop
    ],
    'proud': [
        'spotify:playlist:37i9dQZF1DX1rVvRgjX59F',  # Empowerment
        'spotify:playlist:37i9dQZF1DX9XIFQuFvzM4',  # Confidence
        'spotify:playlist:37i9dQZF1DXcBWIGoYBM5M',  # Today's Top Hits
    ],
    'motivated': [
        'spotify:playlist:37i9dQZF1DX76Wlfdnj7AP',  # Beast Mode
        'spotify:playlist:37i9dQZF1DX3rxVfibe1L0',  # Workout
        'spotify:playlist:37i9dQZF1DX9XIFQuFvzM4',  # Motivation
    ],
    'energetic': [
        'spotify:playlist:37i9dQZF1DX0XUsuxWHRQd',  # Energetic
        'spotify:playlist:37i9dQZF1DX76Wlfdnj7AP',  # Beast Mode
        'spotify:playlist:37i9dQZF1DXdxcBWuJKBcy',  # Cardio
    ],
    'low': [
        'spotify:playlist:37i9dQZF1DX7qK8ma5wgG1',  # Sad
        'spotify:playlist:37i9dQZF1DX7K31D69s4M1',  # Melancholy
        'spotify:playlist:37i9dQZF1DXbYM3nMM0oPk',  # Mood
    ],
    'tired': [
        'spotify:playlist:37i9dQZF1DX3Ogo9pFvBkY',  # Relax
        'spotify:playlist:37i9dQZF1DX4WYpdgoIcn6',  # Chill
        'spotify:playlist:37i9dQZF1DWVrtsSlLKzro',  # Sleep
    ],
    'stressed': [
        'spotify:playlist:37i9dQZF1DWZqd5JICZI0u',  # Stress Relief
        'spotify:playlist:37i9dQZF1DX3Ogo9pFvBkY',  # Calm
        'spotify:playlist:37i9dQZF1DX9XIFQuFvzM4',  # Meditation
    ],
    'anxious': [
        'spotify:playlist:37i9dQZF1DX3Ogo9pFvBkY',  # Calm
        'spotify:playlist:37i9dQZF1DXbYM3nMM0oPk',  # Anxiety Relief
        'spotify:playlist:37i9dQZF1DWZqd5JICZI0u',  # Peace
    ],
    'overwhelmed': [
        'spotify:playlist:37i9dQZF1DX3Ogo9pFvBkY',  # Calm
        'spotify:playlist:37i9dQZF1DXbYM3nMM0oPk',  # Breathe
        'spotify:playlist:37i9dQZF1DWZqd5JICZI0u',  # Serenity
    ],
    'lonely': [
        'spotify:playlist:37i9dQZF1DX7qK8ma5wgG1',  # Comfort
        'spotify:playlist:37i9dQZF1DX3Ogo9pFvBkY',  # Connection
        'spotify:playlist:37i9dQZF1DXbYM3nMM0oPk',  # Warm
    ],
    'irritable': [
        'spotify:playlist:37i9dQZF1DX3Ogo9pFvBkY',  # Calm
        'spotify:playlist:37i9dQZF1DWZqd5JICZI0u',  # Peace
        'spotify:playlist:37i9dQZF1DXbYM3nMM0oPk',  # Relax
    ],
    'confused': [
        'spotify:playlist:37i9dQZF1DX3Ogo9pFvBkY',  # Clarity
        'spotify:playlist:37i9dQZF1DXbYM3nMM0oPk',  # Focus
        'spotify:playlist:37i9dQZF1DX0XUsuxWHRQd',  # Chill
    ],
    'hopeless': [
        'spotify:playlist:37i9dQZF1DX7qK8ma5wgG1',  # Hope
        'spotify:playlist:37i9dQZF1DX3Ogo9pFvBkY',  # Comfort
        'spotify:playlist:37i9dQZF1DWZqd5JICZI0u',  # Light
    ],
    'neutral': [
        'spotify:playlist:37i9dQZF1DXcBWIGoYBM5M',  # Today's Top Hits
        'spotify:playlist:37i9dQZF1DX0XUsuxWHRQd',  # Chill Mix
        'spotify:playlist:37i9dQZF1DX4WYpdgoIcn6',  # Pop Mix
    ],
}

# Mood-based search queries for fallback
MOOD_SEARCH_QUERIES = {
    'happy': 'happy upbeat mood booster',
    'excited': 'excited energetic party',
    'grateful': 'grateful thankful appreciation',
    'hopeful': 'hopeful inspirational uplifting',
    'peaceful': 'peaceful calm relaxation',
    'calm': 'calm relaxing chill',
    'loved': 'love romantic sweet',
    'proud': 'proud confident empowered',
    'motivated': 'motivated workout energy',
    'energetic': 'energetic workout gym',
    'low': 'melancholy sad emotional',
    'tired': 'relaxing sleep chill',
    'stressed': 'stress relief relaxing calm',
    'anxious': 'anxiety relief calming',
    'overwhelmed': 'calming meditation peace',
    'lonely': 'comforting warm cozy',
    'irritable': 'calming peaceful soothing',
    'confused': 'focus clarity chill',
    'hopeless': 'uplifting hopeful inspiring',
    'neutral': 'popular hits 2025',
}

def get_spotify_client():
    """Initialize and return Spotify client"""
    try:
        client_credentials_manager = SpotifyClientCredentials(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET
        )
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        return sp
    except Exception as e:
        print(f"Spotify client error: {e}")
        return None

def get_playlists_for_mood(mood, secondary_mood=None, limit=3):
    """
    Get recommended playlists based on mood
    Returns list of playlist dictionaries with name, description, url, image
    """
    sp = get_spotify_client()
    if not sp:
        return []
    
    playlists = []
    
    # Get primary mood playlists
    primary_playlist_ids = MOOD_PLAYLISTS.get(mood, [])
    
    # Add secondary mood playlists if available
    secondary_playlist_ids = []
    if secondary_mood and secondary_mood in MOOD_PLAYLISTS:
        secondary_playlist_ids = MOOD_PLAYLISTS[secondary_mood]
    
    # Combine and deduplicate
    all_playlist_ids = list(set(primary_playlist_ids + secondary_playlist_ids))
    
    # Randomize to show variety
    random.shuffle(all_playlist_ids)
    
    # Get playlist details from Spotify
    for playlist_id in all_playlist_ids[:limit]:
        try:
            # Extract playlist ID from URI if needed
            if ':' in playlist_id:
                playlist_id = playlist_id.split(':')[-1]
            
            playlist = sp.playlist(playlist_id)
            playlists.append({
                'id': playlist_id,
                'name': playlist['name'],
                'description': playlist['description'][:100] + '...' if playlist['description'] else 'Perfect for your mood',
                'url': playlist['external_urls']['spotify'],
                'image': playlist['images'][0]['url'] if playlist['images'] else None,
                'tracks_url': playlist['tracks']['href'],
                'track_count': playlist['tracks']['total'],
            })
        except Exception as e:
            print(f"Error fetching playlist {playlist_id}: {e}")
            continue
    
    # If no playlists found, search for mood-based playlists
    if not playlists:
        playlists = search_playlists_by_mood(mood, sp, limit)
    
    return playlists

def search_playlists_by_mood(mood, sp=None, limit=3):
    """Fallback: Search Spotify for mood-based playlists"""
    if not sp:
        sp = get_spotify_client()
        if not sp:
            return []
    
    query = MOOD_SEARCH_QUERIES.get(mood, f"{mood} mood playlist")
    playlists = []
    
    try:
        results = sp.search(q=query, type='playlist', limit=limit)
        
        for item in results['playlists']['items']:
            playlists.append({
                'id': item['id'],
                'name': item['name'],
                'description': item['description'][:100] + '...' if item['description'] else f'Curated {mood} playlist',
                'url': item['external_urls']['spotify'],
                'image': item['images'][0]['url'] if item['images'] else None,
                'tracks_url': item['tracks']['href'],
                'track_count': item['tracks']['total'],
            })
    except Exception as e:
        print(f"Error searching playlists: {e}")
    
    return playlists

def get_track_preview(track_id, sp=None):
    """Get 30-second preview URL for a track"""
    if not sp:
        sp = get_spotify_client()
        if not sp:
            return None
    
    try:
        track = sp.track(track_id)
        return track.get('preview_url')
    except:
        return None

def get_mood_based_recommendations(mood, secondary_mood=None, limit=5):
    """
    Get track recommendations based on mood
    Returns list of track dictionaries
    """
    sp = get_spotify_client()
    if not sp:
        return []
    
    # Map mood to audio features
    mood_features = {
        'happy': {'target_valence': 0.8, 'target_energy': 0.7},
        'excited': {'target_valence': 0.7, 'target_energy': 0.9},
        'grateful': {'target_valence': 0.7, 'target_energy': 0.5},
        'hopeful': {'target_valence': 0.7, 'target_energy': 0.6},
        'peaceful': {'target_valence': 0.5, 'target_energy': 0.2},
        'calm': {'target_valence': 0.5, 'target_energy': 0.2},
        'loved': {'target_valence': 0.7, 'target_energy': 0.5},
        'proud': {'target_valence': 0.8, 'target_energy': 0.8},
        'motivated': {'target_valence': 0.8, 'target_energy': 0.8},
        'energetic': {'target_valence': 0.7, 'target_energy': 0.9},
        'low': {'target_valence': 0.2, 'target_energy': 0.3},
        'tired': {'target_valence': 0.3, 'target_energy': 0.2},
        'stressed': {'target_valence': 0.3, 'target_energy': 0.3},
        'anxious': {'target_valence': 0.3, 'target_energy': 0.4},
        'overwhelmed': {'target_valence': 0.3, 'target_energy': 0.2},
        'lonely': {'target_valence': 0.3, 'target_energy': 0.3},
        'irritable': {'target_valence': 0.3, 'target_energy': 0.4},
        'confused': {'target_valence': 0.4, 'target_energy': 0.5},
        'hopeless': {'target_valence': 0.2, 'target_energy': 0.3},
        'neutral': {'target_valence': 0.5, 'target_energy': 0.5},
    }
    
    features = mood_features.get(mood, {'target_valence': 0.5, 'target_energy': 0.5})
    
    try:
        recommendations = sp.recommendations(
            seed_genres=['pop', 'rock', 'electronic', 'chill', 'classical'],
            limit=limit,
            **features
        )
        
        tracks = []
        for track in recommendations['tracks']:
            tracks.append({
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'album': track['album']['name'],
                'preview_url': track['preview_url'],
                'url': track['external_urls']['spotify'],
                'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
            })
        
        return tracks
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return []