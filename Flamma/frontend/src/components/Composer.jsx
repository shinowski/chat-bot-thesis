import { useEffect, useRef, useState } from 'react';

export default function Composer({
  value,
  onChange,
  onSend,
  onImageSelect,
  selectedImage,
  fileInputRef,
  disabled,
  isSending,
}) {
  const taRef = useRef(null);
  const localFileRef = useRef(null);
  const fileRef = fileInputRef || localFileRef;
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    const textarea = taRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  }, [value]);

  const handleSend = () => {
    if (disabled || isSending) return;
    // The textarea stays editable during a reply. Return focus after button
    // clicks so both Enter and Send let the user keep writing immediately.
    taRef.current?.focus({ preventScroll: true });
    onSend();
  };

  useEffect(() => {
    if (!selectedImage) {
      setPreview(null);
      if (fileRef.current) fileRef.current.value = '';
      return;
    }
    const url = URL.createObjectURL(selectedImage);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedImage]);

  const handleInput = (e) => {
    onChange(e.target.value);

  };

  const handleKeyDown = (e) => {
    if (e.nativeEvent.isComposing || e.keyCode === 229) return;
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!e.repeat) handleSend();
    }
  };

  const handleImageChange = (e) => {
    const file = e.target.files?.[0];

    if (!file) return;

    // Only allow image files
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      alert('Please select a JPG, PNG, or WebP image.');
      e.target.value = '';
      return;
    }
    if (file.size >= 10 * 1024 * 1024) {
      alert('Please select an image smaller than 10 MB.');
      e.target.value = '';
      return;
    }

    // Create preview
    // Send selected file to App.jsx
    onImageSelect(file);
    taRef.current?.focus({ preventScroll: true });
  };

  const removeImage = () => {
    setPreview(null);
    onImageSelect(null);

    if (fileRef.current) {
      fileRef.current.value = '';
    }
  };

  return (
    <div className="composer" aria-busy={!!isSending}>

      {preview && (
        <div className="image-preview">
          <img src={preview} alt="Selected skin image" />

          <button
            type="button"
            className="remove-image-btn"
            onClick={removeImage}
            title="Remove image"
          >
            ×
          </button>
        </div>
      )}

      <div className="composer-inner">

        {/* Hidden file input */}
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          onChange={handleImageChange}
          style={{ display: 'none' }}
        />

        {/* Image upload button */}
        <button
          type="button"
          className="icon-btn"
          onClick={() => fileRef.current?.click()}
          disabled={disabled || isSending}
          title="Upload image"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 20 20"
            fill="none"
          >
            <rect
              x="2.5"
              y="4"
              width="15"
              height="12"
              rx="2"
              stroke="currentColor"
              strokeWidth="1.4"
            />

            <circle
              cx="7"
              cy="8.5"
              r="1.4"
              stroke="currentColor"
              strokeWidth="1.4"
            />

            <path
              d="M4 14.5L8 10.5L11 13L14 10L16.5 12.5"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        <textarea
          ref={taRef}
          rows={1}
          placeholder="Ask Flamma..."
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />

        <button
          className="send-btn"
          onClick={handleSend}
          disabled={disabled || isSending || (!value.trim() && !preview)}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
          >
            <path
              d="M2 8H14M14 8L9 3M14 8L9 13"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

      </div>

      <div className="composer-note">
        Ask a follow-up question or send a photo at any time.
      </div>

    </div>
  );
}
