import { useRef, useState } from 'react';

export default function Composer({
  value,
  onChange,
  onSend,
  onImageSelect,
  disabled,
}) {
  const taRef = useRef(null);
  const fileRef = useRef(null);
  const [preview, setPreview] = useState(null);

  const handleInput = (e) => {
    onChange(e.target.value);

    const ta = taRef.current;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const handleImageChange = (e) => {
    const file = e.target.files?.[0];

    if (!file) return;

    // Only allow image files
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file.');
      return;
    }

    // Create preview
    const imageUrl = URL.createObjectURL(file);
    setPreview(imageUrl);

    // Send selected file to App.jsx
    onImageSelect(file);
  };

  const removeImage = () => {
    setPreview(null);
    onImageSelect(null);

    if (fileRef.current) {
      fileRef.current.value = '';
    }
  };

  return (
    <div className="composer">

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
          disabled={disabled}
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
          placeholder="Tell me what's going on..."
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
        />

        <button
          className="send-btn"
          onClick={onSend}
          disabled={disabled || (!value.trim() && !preview)}
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
        Connected to <code>/predict</code> — replies come from your trained model.
      </div>

    </div>
  );
}