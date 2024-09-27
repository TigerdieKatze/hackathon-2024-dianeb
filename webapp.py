from flask import Flask, render_template
import os
from collections import defaultdict

app = Flask(__name__)

DATA_DIR = '/app/data'
RESULTS_FILE = os.path.join(DATA_DIR, 'results.txt')

@app.route('/')
def index():
    total_games = 0
    total_wins = 0
    total_time = 0
    total_turns = 0
    total_new_words_added = 0  # New variable to track words added to the word list
    error_counts_per_word_length = defaultdict(lambda: {'errors': 0, 'games': 0})

    try:
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Parse the line
                parts = line.split(',')
                if len(parts) != 6:
                    continue
                result, word_length_str, error_count_str, total_time_str, num_turns_str, word_added = parts
                word_length = int(word_length_str)
                error_count = int(error_count_str)
                game_total_time = float(total_time_str)
                game_num_turns = int(num_turns_str)
                total_games += 1
                if result == 'win':
                    total_wins += 1
                error_counts_per_word_length[word_length]['errors'] += error_count
                error_counts_per_word_length[word_length]['games'] += 1
                total_time += game_total_time
                total_turns += game_num_turns
                if word_added == 'yes':
                    total_new_words_added += 1  # Increment the counter

    except FileNotFoundError:
        return "Results file not found. No statistics to display."
    except Exception as e:
        return f"Error reading results file: {e}"

    win_percentage = (total_wins / total_games * 100) if total_games > 0 else 0
    avg_time_per_turn = (total_time / total_turns) if total_turns > 0 else 0
    avg_errors = sum(data['errors'] for data in error_counts_per_word_length.values()) / total_games if total_games > 0 else 0

    stats = {
        'total_games': total_games,
        'total_wins': total_wins,
        'win_percentage': win_percentage,
        'avg_time_per_turn': avg_time_per_turn,
        'error_counts_per_word_length': dict(error_counts_per_word_length),
        'avg_errors': avg_errors,
        'total_new_words_added': total_new_words_added  # Pass the new statistic to the template
    }

    return render_template('index.html', stats=stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
