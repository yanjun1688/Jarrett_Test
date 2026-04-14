import React from 'react';

const ReactMarkdown = ({ children, remarkPlugins }) => {
  return (
    <div className="markdown-content" data-testid="markdown-mock">
      {children}
    </div>
  );
};

export default ReactMarkdown;