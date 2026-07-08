import { cn } from '@/lib/utils';

function ReviewActions({ className, ...props }) {
  return (
    <div
      className={cn('script-review-actions', className)}
      {...props}
    />
  );
}

function ReviewActionsContent({ className, ...props }) {
  return (
    <div
      className={cn('script-review-actions-content', className)}
      {...props}
    />
  );
}

function ReviewActionsTitle({ className, ...props }) {
  return (
    <strong
      className={cn('script-review-actions-title', className)}
      {...props}
    />
  );
}

function ReviewActionsDescription({ className, ...props }) {
  return (
    <span
      className={cn('script-review-actions-description', className)}
      {...props}
    />
  );
}

export {
  ReviewActions,
  ReviewActionsContent,
  ReviewActionsDescription,
  ReviewActionsTitle,
};
