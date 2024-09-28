from flask import Flask, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    DATA_DIR = os.getcwd()
    RESULTS_FILE = os.path.join(DATA_DIR, 'data', 'results.txt')

    total_games = 0
    total_wins = 0
    total_time = 0.0
    total_turns = 0
    total_new_words_added = 0
    error_counts_per_word_length = {}

    try:
        with open(RESULTS_FILE, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue  # Skip empty lines

                parts = line.split(',')
                if len(parts) != 6:
                    # Optionally handle malformed lines
                    continue

                result, word_length_str, error_count_str, total_time_str, num_turns_str, word_added = parts

                try:
                    word_length = int(word_length_str)
                    error_count = int(error_count_str)
                    game_total_time = float(total_time_str)
                    num_turns_game = int(num_turns_str)
                except ValueError:
                    # Skip lines with invalid numerical values
                    continue

                total_games += 1
                if result.lower() == 'win':
                    total_wins += 1

                if word_length not in error_counts_per_word_length:
                    error_counts_per_word_length[word_length] = {'errors': 0, 'games': 0}

                error_counts_per_word_length[word_length]['errors'] += error_count
                error_counts_per_word_length[word_length]['games'] += 1

                total_time += game_total_time
                total_turns += num_turns_game

                if word_added.lower() == 'yes':
                    total_new_words_added += 1

        # Calculate statistics
        win_percentage = (total_wins / total_games) * 100 if total_games > 0 else 0
        avg_time_per_turn = (total_time / total_turns) if total_turns > 0 else 0
        total_errors = sum(v['errors'] for v in error_counts_per_word_length.values())
        avg_errors = (total_errors / total_games) if total_games > 0 else 0

        # Convert keys of error_counts_per_word_length to strings for JSON compatibility
        error_counts_per_word_length_str_keys = {str(k): v for k, v in error_counts_per_word_length.items()}

        response = {
            'total_games': total_games,
            'total_wins': total_wins,
            'win_percentage': win_percentage,
            'avg_time_per_turn': avg_time_per_turn,
            'avg_errors': avg_errors,
            'total_new_words_added': total_new_words_added,
            'error_counts_per_word_length': error_counts_per_word_length_str_keys
        }

        return jsonify(response), 200

    except FileNotFoundError:
        return jsonify({'error': 'Results file not found'}), 500
    except Exception as e:
        print(f'Error reading results file: {e}')
        return jsonify({'error': 'Failed to read results file'}), 500

if __name__ == '__main__':
    # Run the Flask app on port 5000 by default
    app.run(host='0.0.0.0', port=5000, debug=True)
