import { ApiError } from '../../types/apiError';
import { friendlyErrorMessage } from '../../utils/apiErrorMessages';
import { Button } from '../ui/Button';
import styles from '../ui/ui.module.css';

interface ErrorBannerProps {
  error: unknown;
  onRetry?: () => void;
}

export function ErrorBanner({ error, onRetry }: ErrorBannerProps) {
  if (!error) return null;

  let message: string;
  if (error instanceof ApiError) {
    if (error.status === 403) {
      message = "You don't have permission to view this.";
    } else {
      message = friendlyErrorMessage(error.code, error.detail);
    }
  } else if (error instanceof Error) {
    message = error.message;
  } else {
    message = 'Something went wrong.';
  }

  return (
    <div className={styles.errorBanner} data-testid="error-banner">
      <span>{message}</span>
      {onRetry && (
        <Button onClick={onRetry} type="button">
          Retry
        </Button>
      )}
    </div>
  );
}
