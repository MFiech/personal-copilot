import React from 'react';
import {
  Box,
  Typography,
  Chip,
  IconButton,
  Divider
} from '@mui/material';
import EventIcon from '@mui/icons-material/Event';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import DescriptionIcon from '@mui/icons-material/Description';
import GroupIcon from '@mui/icons-material/Group';
import LaunchIcon from '@mui/icons-material/Launch';

const CalendarEventComponent = ({
  event,
  showHeader = true,
  showActions = false
}) => {
  if (!event) return null;

  const formatDateTime = (dateTimeString) => {
    if (!dateTimeString) return 'Not specified';
    try {
      const date = new Date(dateTimeString);
      return date.toLocaleString([], {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      console.error('Error formatting date:', error);
      return dateTimeString;
    }
  };

  const getEventDates = () => {
    const start = event.start?.dateTime || event.start?.date;
    const end = event.end?.dateTime || event.end?.date;

    if (!start) return 'No date specified';

    const startDate = new Date(start);
    const endDate = end ? new Date(end) : null;

    // Check if it's an all-day event
    const isAllDay = !event.start?.dateTime;

    if (isAllDay) {
      return startDate.toLocaleDateString([], {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    }

    const startStr = formatDateTime(start);
    const endStr = endDate ? formatDateTime(end) : '';

    return endStr ? `${startStr} - ${endStr}` : startStr;
  };

  return (
    <Box sx={{ p: 2 }}>
      {showHeader && (
        <>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <EventIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              Calendar Event
            </Typography>
            {showActions && (
              <IconButton
                size="small"
                sx={{ ml: 'auto' }}
                title="Open in Google Calendar"
              >
                <LaunchIcon />
              </IconButton>
            )}
          </Box>
          <Divider sx={{ mb: 2 }} />
        </>
      )}

      {/* Event Title */}
      <Typography
        variant="subtitle1"
        sx={{ fontWeight: 'bold', mb: 1, color: 'text.primary' }}
      >
        {event.summary || 'Untitled Event'}
      </Typography>

      {/* Date and Time */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          {getEventDates()}
        </Typography>
      </Box>

      {/* Location */}
      {event.location && (
        <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
          <LocationOnIcon sx={{ fontSize: 16, mr: 1, mt: 0.5, color: 'text.secondary' }} />
          <Typography variant="body2" color="text.secondary">
            {event.location}
          </Typography>
        </Box>
      )}

      {/* Description */}
      {event.description && (
        <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
          <DescriptionIcon sx={{ fontSize: 16, mr: 1, mt: 0.5, color: 'text.secondary' }} />
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}
          >
            {event.description.length > 200
              ? `${event.description.substring(0, 200)}...`
              : event.description
            }
          </Typography>
        </Box>
      )}

      {/* Attendees */}
      {event.attendees && event.attendees.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <GroupIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
            <Typography variant="body2" color="text.secondary" fontWeight="medium">
              Attendees ({event.attendees.length})
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {event.attendees.slice(0, 3).map((attendee, index) => (
              <Chip
                key={index}
                label={attendee.email || attendee}
                size="small"
                variant="outlined"
                sx={{ fontSize: '0.75rem' }}
              />
            ))}
            {event.attendees.length > 3 && (
              <Chip
                label={`+${event.attendees.length - 3} more`}
                size="small"
                variant="outlined"
                sx={{ fontSize: '0.75rem' }}
              />
            )}
          </Box>
        </Box>
      )}

      {/* Event Status */}
      {event.status && (
        <Box sx={{ mt: 2 }}>
          <Chip
            label={event.status.charAt(0).toUpperCase() + event.status.slice(1)}
            size="small"
            color={event.status === 'confirmed' ? 'success' : 'default'}
            variant="filled"
          />
        </Box>
      )}
    </Box>
  );
};

export default CalendarEventComponent;