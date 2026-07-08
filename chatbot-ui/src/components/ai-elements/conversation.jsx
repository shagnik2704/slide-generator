import { cn } from '@/lib/utils';

function Conversation({ className, ...props }) {
  return (
    <section
      className={cn('script-conversation', className)}
      {...props}
    />
  );
}

function ConversationContent({ className, ...props }) {
  return (
    <div
      className={cn('script-conversation-content', className)}
      {...props}
    />
  );
}

function ConversationEmptyState({
  className,
  description,
  icon,
  title,
  ...props
}) {
  return (
    <div
      className={cn('script-conversation-empty', className)}
      {...props}
    >
      {icon && <div className="script-conversation-empty-icon">{icon}</div>}
      <div>
        <h3>{title}</h3>
        {description && <p>{description}</p>}
      </div>
    </div>
  );
}

export { Conversation, ConversationContent, ConversationEmptyState };
