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
    error_counts_per_word_length = defaultdict(lambda: {'errors': 0, 'games': 0})

    try:
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Parse the line
                parts = line.split(',')
                if len(parts) != 3:
                    continue
                result, word_length_str, error_count_str = parts
                word_length = int(word_length_str)
                error_count = int(error_count_str)
                total_games += 1
                if result == 'win':
                    total_wins += 1
                error_counts_per_word_length[word_length]['errors'] += error_count
                error_counts_per_word_length[word_length]['games'] += 1

    except FileNotFoundError:
        return "Results file not found. No statistics to display."
    except Exception as e:
        return f"Error reading results file: {e}"

    win_percentage = (total_wins / total_games * 100) if total_games > 0 else 0

    stats = {
        'total_games': total_games,
        'total_wins': total_wins,
        'win_percentage': win_percentage,
        'error_counts_per_word_length': dict(error_counts_per_word_length)
    }

    return render_template('index.html', stats=stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
