import React, { useRef, useEffect, useState } from 'react';
import {
    Box,
    Button,
    ColumnLayout,
    SpaceBetween,
    TextFilter,
    Toggle,
    StatusIndicator,
    Link
} from '@cloudscape-design/components';
import { useStore } from '../../store';
import { Download, Copy, Trash2 } from 'lucide-react';

interface Message {
    id: string;
    from: string;
    to: string;
    type: string;
    content: Record<string, any>;
    timestamp: number;
}

const MessageLog: React.FC = () => {
    const messages = useStore(state => state.messages);
    const resetLogs = useStore(state => state.resetLogs);
    const logRef = useRef<HTMLDivElement>(null);
    const [filterText, setFilterText] = useState('');
    const [autoScroll, setAutoScroll] = useState(true);
    const [showTimestamps, setShowTimestamps] = useState(true);
    const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());

    // Auto-scroll when new messages arrive
    useEffect(() => {
        if (autoScroll && logRef.current) {
            logRef.current.scrollTop = logRef.current.scrollHeight;
        }
    }, [messages, autoScroll]);

    const filteredMessages = messages.filter(msg => {
        const searchText = filterText.toLowerCase();
        return (
            msg.type.toLowerCase().includes(searchText) ||
            msg.from.toLowerCase().includes(searchText) ||
            msg.to.toLowerCase().includes(searchText) ||
            JSON.stringify(msg.content).toLowerCase().includes(searchText)
        );
    });

    const toggleMessageExpand = (messageId: string) => {
        const newExpanded = new Set(expandedMessages);
        if (newExpanded.has(messageId)) {
            newExpanded.delete(messageId);
        } else {
            newExpanded.add(messageId);
        }
        setExpandedMessages(newExpanded);
    };

    const downloadLogs = () => {
        const logData = JSON.stringify(messages, null, 2);
        const blob = new Blob([logData], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `lightning-message-log-${new Date().toISOString()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const copyToClipboard = () => {
        const logData = JSON.stringify(messages, null, 2);
        navigator.clipboard.writeText(logData);
    };

    const getMessageStatusColor = (type: string) => {
        switch (type.toLowerCase()) {
            case 'error':
                return 'error';
            case 'warning':
                return 'warning';
            case 'init':
                return 'info';
            case 'ping':
            case 'pong':
                return 'success';
            default:
                return 'info';
        }
    };

    return (
        <Box>
            <SpaceBetween size="s">
                {/* Controls */}
                <ColumnLayout columns={3} variant="text-grid">
                    <SpaceBetween direction="horizontal" size="xs">
                        <TextFilter
                            filteringText={filterText}
                            onChange={({ detail }) => setFilterText(detail.filteringText)}
                            placeholder="Filter messages..."
                            countText={`${filteredMessages.length} matches`}
                        />
                    </SpaceBetween>
                    <SpaceBetween direction="horizontal" size="xs">
                        <Toggle
                            onChange={({ detail }) => setAutoScroll(detail.checked)}
                            checked={autoScroll}
                        >
                            Auto-scroll
                        </Toggle>
                        <Toggle
                            onChange={({ detail }) => setShowTimestamps(detail.checked)}
                            checked={showTimestamps}
                        >
                            Show timestamps
                        </Toggle>
                    </SpaceBetween>
                    <SpaceBetween direction="horizontal" size="xs">
                        <Button
                            iconAlign="left"
                            onClick={downloadLogs}
                            icon={<Download size={16} />}
                        >
                            Download
                        </Button>
                        <Button
                            iconAlign="left"
                            onClick={copyToClipboard}
                            icon={<Copy size={16} />}
                        >
                            Copy
                        </Button>
                        <Button
                            iconAlign="left"
                            onClick={resetLogs}
                            icon={<Trash2 size={16} />}
                        >
                            Clear
                        </Button>
                    </SpaceBetween>
                </ColumnLayout>

                {/* Message Log */}
                <div
                    ref={logRef}
                    className="bg-white border border-gray-200 rounded-md p-2 h-[300px] overflow-y-auto message-log"
                >
                    {filteredMessages.length === 0 ? (
                        <div className="text-xs text-gray-500 text-center py-4">
                            {filterText ? 'No messages match the filter' : 'No messages exchanged yet'}
                        </div>
                    ) : (
                        filteredMessages.map((msg) => (
                            <div
                                key={msg.id}
                                className="text-xs mb-2 p-2 rounded hover:bg-gray-50 transition-colors"
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center space-x-2">
                                        {showTimestamps && (
                                            <span className="text-gray-500">
                                                {new Date(msg.timestamp).toLocaleTimeString()}
                                            </span>
                                        )}
                                        <StatusIndicator type={getMessageStatusColor(msg.type)}>
                                            {msg.type.toUpperCase()}
                                        </StatusIndicator>
                                        <span className={msg.from === 'runner' ? 'text-blue-600' : 'text-yellow-600'}>
                                            {msg.from.toUpperCase()}
                                        </span>
                                        <span>→</span>
                                        <span className={msg.to === 'runner' ? 'text-blue-600' : 'text-yellow-600'}>
                                            {msg.to.toUpperCase()}
                                        </span>
                                    </div>
                                    <Link
                                        onFollow={() => toggleMessageExpand(msg.id)}
                                        variant="info"
                                    >
                                        {expandedMessages.has(msg.id) ? 'Collapse' : 'Expand'}
                                    </Link>
                                </div>
                                {expandedMessages.has(msg.id) && (
                                    <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-x-auto">
                                        {JSON.stringify(msg.content, null, 2)}
                                    </pre>
                                )}
                            </div>
                        ))
                    )}
                </div>
            </SpaceBetween>
        </Box>
    );
};

export default MessageLog; 