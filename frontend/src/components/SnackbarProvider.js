import React, { createContext, useContext, useState, useCallback } from 'react';
import Snackbar from '@mui/material/Snackbar';
import MuiAlert from '@mui/material/Alert';

const SnackbarContext = createContext();

export const useSnackbar = () => useContext(SnackbarContext);

export const SnackbarProvider = ({ children }) => {
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  const showSnackbar = useCallback((message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  }, []);

  const handleClose = () => setSnackbar(s => ({ ...s, open: false }));

  return (
    <SnackbarContext.Provider value={{ showSnackbar }}>
      {children}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={5000}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
        sx={{
          '& .MuiPaper-root': {
            minWidth: 350,
            maxWidth: 500,
            fontSize: '1.25rem',
            padding: '18px 28px',
            borderRadius: 3,
          },
        }}
      >
        <MuiAlert
          onClose={handleClose}
          severity={snackbar.severity}
          sx={{
            width: '100%',
            fontSize: '1.15rem',
            padding: '18px 28px',
            borderRadius: 3,
          }}
        >
          {snackbar.message}
        </MuiAlert>
      </Snackbar>
    </SnackbarContext.Provider>
  );
}; 