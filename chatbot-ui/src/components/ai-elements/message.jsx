import { cn } from '@/lib/utils';

function Message({ className, from = 'assistant', ...props }) {
  return (
    <article
      className={cn('script-ai-message', `script-ai-message-${from}`, className)}
      {...props}
    />
  );
}

function MessageContent({ className, ...props }) {
  return (
    <div
      className={cn('script-ai-message-content', className)}
      {...props}
    />
  );
}

function MessageLabel({ children, className, ...props }) {
  return (
    <span
      className={cn('script-ai-message-label', className)}
      {...props}
    >
      {children}
    </span>
  );
}

export { Message, MessageContent, MessageLabel };
