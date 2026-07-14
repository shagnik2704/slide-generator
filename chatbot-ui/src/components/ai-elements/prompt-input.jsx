import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

function PromptInput({ className, ...props }) {
  return (
    <form
      className={cn('script-prompt-input', className)}
      {...props}
    />
  );
}

function PromptInputTextarea({ className, ...props }) {
  return (
    <Textarea
      className={cn('script-prompt-textarea', className)}
      {...props}
    />
  );
}

function PromptInputFooter({ className, ...props }) {
  return (
    <div
      className={cn('script-prompt-footer', className)}
      {...props}
    />
  );
}

function PromptInputTools({ className, ...props }) {
  return (
    <div
      className={cn('script-prompt-tools', className)}
      {...props}
    />
  );
}

function PromptInputSubmit({ children, className, ...props }) {
  return (
    <Button
      className={cn('script-prompt-submit', className)}
      type="submit"
      {...props}
    >
      {children}
    </Button>
  );
}

export {
  PromptInput,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
};
