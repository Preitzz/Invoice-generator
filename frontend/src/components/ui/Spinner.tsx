import styles from './ui.module.css';

export function Spinner() {
  return (
    <div className={styles.spinnerWrap} data-testid="spinner">
      <div className={styles.spinner} />
    </div>
  );
}
