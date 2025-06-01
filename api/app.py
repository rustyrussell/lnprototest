import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import necessary libraries
from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import json
from lnprototest.dummyrunner import DummyRunner
from lnprototest.event import Msg, ExpectMsg, Connect
from lnprototest.runner import Conn
import re
import traceback

# Create a mock config class to satisfy Runner's expectations
class MockConfig:
    def getoption(self, name):
        if name == "verbose":
            return True
        raise AttributeError(f"Unknown option: {name}")

# Create a Flask app
app = Flask(__name__)
# Enable CORS for all origins in development
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize DummyRunner with the mock config
mock_config = MockConfig()
runner = DummyRunner(config=mock_config)
runner.start()

# Helper functions
def is_valid_hex(s):
    if not isinstance(s, str):
        return False
    return bool(re.match(r'^[0-9a-fA-F]*$', s))

def get_message_fields(msg_tuple):
    """Extract message fields from a message tuple returned by runner.get_stash()"""
    if not msg_tuple or len(msg_tuple) < 2:
        return {}
    
    # The second element contains the message fields
    fields = msg_tuple[1]
    # Convert all fields to strings for consistent JSON serialization
    return {k: str(v) if v is not None else '' for k, v in fields.items()}

def expect_response(msg_type, conn_privkey):
    """Helper function to expect and handle response messages"""
    response_types = {
        'init': 'init',
        'ping': 'pong',
        # Add more message type mappings as needed
    }
    
    if msg_type not in response_types:
        return None
        
    expect_msg = ExpectMsg(response_types[msg_type], connprivkey=conn_privkey)
    expect_msg.action(runner)
    received_msgs = runner.get_stash(expect_msg, "ExpectMsg", [])
    return received_msgs[-1] if received_msgs else None

# Error handler
@app.errorhandler(Exception)
def handle_error(error):
    print(f"Error: {str(error)}")
    print(traceback.format_exc())
    return jsonify({
        'error': str(error),
        'type': type(error).__name__
    }), 500

# Health check
@app.route('/health', methods=['GET'])
def health_check():
    # Use IST timezone (UTC+5:30)
    ist_time = time.strftime('%Y-%m-%d %H:%M:%S IST', time.localtime(time.time() + 19800))
    return jsonify({
        'status': 'healthy',
        'time': ist_time,
        'message': 'API is running',
        'runner_status': 'running' if runner.is_running() else 'stopped'
    }), 200

# Node info endpoint
@app.route('/node-info', methods=['GET'])
def node_info():
    return jsonify({
        'node_id': runner.get_node_privkey(),
        'bitcoin_key': runner.get_node_bitcoinkey(),
        'active_connections': len(runner.conns),
        'features': runner.runner_features()
    }), 200

def handle_message_flow(msg_type, content=None):
    """Helper to handle message flow and responses"""
    try:
        msg = Msg(msg_type, connprivkey='02', **(content or {}))
        msg.action(runner)
        
        messages = [{
            'from': 'runner', 
            'to': 'ldk', 
            'type': msg_type,
            'content': runner.get_stash(msg, "Msg", [])[-1][1]
        }]
        
        # Handle responses for init and ping
        if msg_type in ['init', 'ping']:
            response_type = 'pong' if msg_type == 'ping' else msg_type
            expect = ExpectMsg(response_type, connprivkey='02')
            expect.action(runner)
            received = runner.get_stash(expect, "ExpectMsg", [])[-1]
            messages.append({
                'from': 'ldk',
                'to': 'runner',
                'type': response_type,
                'content': received[1]
            })
        
        return messages
    except Exception as e:
        print(f"Error in handle_message_flow: {str(e)}")
        print(traceback.format_exc())
        raise

# Connect endpoint - performs full connection handshake
@app.route('/connect', methods=['POST', 'OPTIONS'])
def connect():
    """Establish connection between two nodes (involves 2 raw messages)"""
    try:
        # First establish the connection
        Connect('02').action(runner)
        
        # Then send init message with empty features
        messages = handle_message_flow('init', {
            'globalfeatures': '',
            'features': ''
        })
        
        return jsonify({
            'messages': messages,
            'status': 'connected',
            'node_id': runner.get_node_privkey()
        })
    except Exception as e:
        print(f"Error in connect: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'type': type(e).__name__
        }), 500

# Raw message endpoint - sends a single message
@app.route('/raw-msg', methods=['POST', 'OPTIONS'])
def raw_msg():
    """Send a single raw message to the other node"""
    try:
        data = request.json
        if not data or 'msg' not in data or 'type' not in data:
            return jsonify({
                'error': 'Invalid request format. Required fields: msg, type',
                'type': 'ValidationError'
            }), 400

        # Create message with all provided fields
        msg_content = {k: v for k, v in data.items() if k != 'msg'}
        messages = handle_message_flow(data['msg'], msg_content)
        return jsonify({'messages': messages})
    except Exception as e:
        print(f"Error in raw_msg: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'type': type(e).__name__
        }), 500

@app.route('/messages', methods=['GET'])
def get_messages():
    try:
        # Assuming runner.get_logs() returns a list of messages
        logs = runner.get_logs() if hasattr(runner, 'get_logs') else []
        return jsonify({'messages': logs})
    except Exception as e:
        print(f"Error in get_messages: {str(e)}")
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        runner.stop()
        runner.teardown()