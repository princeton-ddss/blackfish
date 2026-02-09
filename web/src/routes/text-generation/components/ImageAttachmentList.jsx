import ImageAttachment from "./ImageAttachment";
import PropTypes from "prop-types";

/**
 * Horizontal scrollable list of image attachments.
 * @param {object} props
 * @param {Array} props.images - Array of image objects.
 * @param {Function} props.onRemove - Callback to remove an image by index.
 * @param {Function} props.onImageError - Callback when an image fails to load.
 * @param {Function} props.onImageLoad - Callback when an image loads, receives (index, base64).
 */
function ImageAttachmentList({ images, onRemove, onImageError, onImageLoad }) {
  if (!images || images.length === 0) {
    return null;
  }

  return (
    <div className="flex gap-2 overflow-x-auto pt-3 pb-2 pr-3">
      {images.map((image, index) => (
        <ImageAttachment
          key={`${image.source}-${image.source === "browser" ? image.file.name : image.path}-${index}`}
          image={image}
          onRemove={onRemove}
          onError={onImageError}
          onLoad={onImageLoad}
          index={index}
        />
      ))}
    </div>
  );
}

ImageAttachmentList.propTypes = {
  images: PropTypes.arrayOf(
    PropTypes.shape({
      source: PropTypes.oneOf(["browser", "remote"]).isRequired,
      file: PropTypes.object,
      path: PropTypes.string,
      profile: PropTypes.object,
    })
  ).isRequired,
  onRemove: PropTypes.func.isRequired,
  onImageError: PropTypes.func,
  onImageLoad: PropTypes.func,
};

export default ImageAttachmentList;
