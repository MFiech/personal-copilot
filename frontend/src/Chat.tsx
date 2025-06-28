import React, { useState, useEffect, useRef, useCallback } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import ToolTile from './components/ToolTile';
import './components/ToolTile.css';
import { Message } from './components/Message';
import { ChatInput } from './components/ChatInput';
import { ProfileSwitcher } from './ProfileSwitcher';
import SelectionControlPanel from './SelectionControlPanel';

const ctrlClickListener = (event: KeyboardEvent) => {
  if (event.key === 'k' && (event.metaKey || event.ctrlKey)) {
    // Example: console.log("Ctrl+K pressed");
    // Actual implementation of what Ctrl+K should do
  }
};

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'function';
  content: string;
  name?: string;
  createdAt: Date;
  parts: { 
    type: 'text' | 'tile'; 
    content?: string; 
    tileData?: { 
      id: string;
      type: 'email' | 'calendar';
      [key: string]: any;
    }; 
  }[];
}

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentProfile, setCurrentProfile] = useState('default');
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [showProfileSwitcher, setShowProfileSwitcher] = useState(false);

  const [selectedTiles, setSelectedTiles] = useState<Record<string, boolean>>({});
  const [activeSelectionMessageId, setActiveSelectionMessageId] = useState<string | null>(null);
  const [hoveredTileKey, setHoveredTileKey] = useState<string | null>(null);

  useEffect(() => {
    // Original useEffect content should be here
    // Example: document.addEventListener('keydown', ctrlClickListener);
    // return () => document.removeEventListener('keydown', ctrlClickListener);
  }, []);

  useEffect(() => {
    // Original useEffect content for messages changes should be here
    // Example: if (chatContainerRef.current) chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
  }, [messages]);

  const handleProfileSwitch = (profile: string) => {
    setCurrentProfile(profile);
    setShowProfileSwitcher(false);
    // Potentially clear messages or other profile-specific state
    // setMessages([]); 
    console.log("Switched to profile:", profile);
  };

  const processStreamedData = useCallback((data: any): Partial<ChatMessage> => {
    // Original processStreamedData content should be here
    // This function is responsible for parsing the streamed data from the server
    // and converting it into a Partial<ChatMessage> object.
    // For example:
    // if (data.type === 'text_delta') return { parts: [{ type: 'text', content: data.delta }] };
    // if (data.type === 'tile') return { parts: [{ type: 'tile', tileData: data.tileData }] };
    return {}; // Placeholder return
  }, []);

  const handleTileSelect = (messageId: string, tileId: string) => {
    const key = `${messageId}-${tileId}`;
    setSelectedTiles(prev => {
      const newSelected = { ...prev };
      if (activeSelectionMessageId === null) {
        setActiveSelectionMessageId(messageId);
        newSelected[key] = true;
      } else if (activeSelectionMessageId === messageId) {
        if (newSelected[key]) {
          delete newSelected[key];
        } else {
          newSelected[key] = true;
        }
        const remainingInMessage = Object.keys(newSelected).filter(k => k.startsWith(messageId + '-')).length;
        if (remainingInMessage === 0) {
           setActiveSelectionMessageId(null); 
        }
        if (Object.keys(newSelected).length === 0) {
           setActiveSelectionMessageId(null);
        }
      }
      return newSelected;
    });
  };

  const handleDeselectAll = () => {
    setSelectedTiles({});
    setActiveSelectionMessageId(null);
  };

  const handleSelectAll = () => {
    if (activeSelectionMessageId) {
      const newSelectedTiles = { ...selectedTiles };
      const activeMessage = messages.find(msg => msg.id === activeSelectionMessageId);
      if (activeMessage) {
        activeMessage.parts.forEach(part => {
          if (part.type === 'tile' && part.tileData) {
            // Ensure a unique enough ID if tileData.id is not present
            const tileId = part.tileData.id || `fallback-id-${part.tileData.type}-${Math.random().toString(36).substring(7)}`;
            const key = `${activeSelectionMessageId}-${tileId}`;
            newSelectedTiles[key] = true;
          }
        });
        setSelectedTiles(newSelectedTiles);
      }
    }
    // If no activeSelectionMessageId, "Select All" doesn't have a clear context, so we do nothing.
  };

  const handleSubmit = async (event?: React.FormEvent<HTMLFormElement>, messageContent?: string) => {
    if (event) event.preventDefault();
    const currentInput = messageContent || input;
    if (!currentInput.trim() && !messages.find(msg => msg.role === 'user' && msg.content.includes('file:'))) {
      return;
    }

    setIsLoading(true);
    const userMessage: ChatMessage = {
      id: 'user-' + Date.now(),
      role: 'user',
      content: currentInput,
      createdAt: new Date(),
      parts: [{ type: 'text', content: currentInput }],
    };
    setMessages(prevMessages => [...prevMessages, userMessage]);
    setInput('');

    // Retain the last assistant message ID if available for context
    let lastAssistantMessageId: string | null = null;
    for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'assistant') {
            lastAssistantMessageId = messages[i].id;
            break;
        }
    }

    try {
      // Use regular fetch instead of streaming for now
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: currentInput,
          profile: currentProfile,
          lastAssistantMessageId: lastAssistantMessageId,
        }),
      });

      if (!response.ok) {
        setIsLoading(false);
        const errorText = await response.text();
        setMessages(prev => [...prev, {
          id: 'err-' + Date.now(),
          role: 'system',
          content: `Error: ${response.status} ${response.statusText} - ${errorText}`,
          createdAt: new Date(),
          parts: [{ type: 'text', content: `Error: ${response.status} ${response.statusText} - ${errorText}`}]
        }]);
        return;
      }

      const data = await response.json();
      console.log('Received response:', data);

      // Create the assistant message from the response
      const assistantMessage: ChatMessage = {
        id: data.message_id || 'ast-' + Date.now(),
        role: 'assistant',
        content: data.response || '',
        createdAt: new Date(),
        parts: [],
      };

      // Add text content as the first part
      if (data.response) {
        assistantMessage.parts.push({
          type: 'text',
          content: data.response
        });
      }

      // Process tool results to create tiles
      if (data.tool_results && data.tool_results.tiles) {
        console.log('Processing tiles:', data.tool_results.tiles);
        data.tool_results.tiles.forEach((tileData: any) => {
          assistantMessage.parts.push({
            type: 'tile',
            tileData: tileData
          });
        });
      }

      setMessages(prev => [...prev, assistantMessage]);
      setIsLoading(false);
    } catch (error) {
      console.error('Failed to send message:', error);
      setIsLoading(false);
      setMessages(prev => [...prev, {
        id: 'err-' + Date.now(),
        role: 'system',
        content: 'Failed to send the message. Please check your connection or contact support.',
        createdAt: new Date(),
        parts: [{ type: 'text', content: 'Failed to send the message. Please check your connection or contact support.'}]
      }]);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-gray-800">
      <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Chat Interface</h1>
        <ProfileSwitcher currentProfile={currentProfile} onProfileSwitch={handleProfileSwitch} />
      </div>

      <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, msgIndex) => (
          <Message key={message.id + '-' + msgIndex} message={message}>
            <div className="flex flex-wrap">
              {message.parts.map((part, partIndex) => {
                if (part.type === 'tile' && part.tileData) {
                  const tileId = part.tileData.id || `fallback-id-${partIndex}`;
                  const tileKey = `${message.id}-${tileId}`;
                  const isChecked = !!selectedTiles[tileKey];
                  const isDisabled = activeSelectionMessageId !== null && activeSelectionMessageId !== message.id;
                  const isCheckboxVisible = hoveredTileKey === tileKey || isChecked;
                  
                  return (
                    <div 
                      key={tileKey}
                      className={`relative tile-container m-1 ${isChecked ? 'ring-2 ring-blue-500' : ''}`}
                      onMouseEnter={() => setHoveredTileKey(tileKey)}
                      onMouseLeave={() => setHoveredTileKey(null)}
                    >
                       {isCheckboxVisible && (
                         <div className="absolute bottom-0 right-0 w-8 h-8 bg-white bg-opacity-80 rounded-tl-md z-[9998]"></div>
                       )}
                       <input
                        type="checkbox"
                        className="absolute bottom-1 right-1 z-[9999] tile-checkbox pointer-events-auto w-5 h-5"
                        style={{
                          opacity: isCheckboxVisible ? 1 : 0,
                          transition: 'opacity 0.2s ease-in-out',
                          backgroundColor: 'white',
                          border: '2px solid #1976d2' 
                        }}
                        checked={isChecked}
                        disabled={isDisabled}
                        onChange={() => handleTileSelect(message.id, tileId)}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <ToolTile 
                        type={part.tileData.type || 'email'}
                        data={part.tileData}
                      />
                    </div>
                  );
                }
                return null; 
              })}
            </div>
          </Message>
        ))}
      </div>
      
      {Object.keys(selectedTiles).length > 0 && (
        <SelectionControlPanel
          selectedCount={Object.keys(selectedTiles).length}
          onSelectAll={handleSelectAll}
          onDeselectAll={handleDeselectAll}
          onSummarize={() => console.log('Summarize clicked. Selected:', selectedTiles)}
          onDelete={() => console.log('Delete clicked. Selected:', selectedTiles)}
        />
      )}

      <div className="fixed bottom-0 left-0 right-0 p-2 sm:p-4 bg-white dark:bg-gray-800 border-t dark:border-gray-700">
        <ChatInput
          input={input}
          setInput={setInput}
          handleSubmit={handleSubmit}
          isLoading={isLoading}
          onUploadSuccess={(filename, content) => {
            // For onUploadSuccess, assuming it updates input or calls handleSubmit
            setInput(`File uploaded: ${filename}. Describe or ask questions about it.`);
            // Or perhaps, it directly forms a message and calls handleSubmit
            // handleSubmit(undefined, `File uploaded: ${filename}`);
          }}
          onUploadFailure={(filename, error) => {
            console.error('Upload failed:', filename, error);
            setMessages(prev => [...prev, {
                id: 'err-upload-' + Date.now(),
                role: 'system',
                content: `Failed to upload file ${filename}: ${error}`,
                createdAt: new Date(),
                parts: [{ type: 'text', content: `Failed to upload file ${filename}: ${error}`}]
              }]);
          }}
        />
      </div>
      <style>{`
        .tile-checkbox {
           cursor: pointer;
        }
      `}</style>
    </div>
  );
};

export default Chat; 