import ImageAttachment from "./ImageAttachment";
import PropTypes from "prop-types";

/**
 * Horizontal scrollable list of image attachments.
 * @param {object} props
 * @param {Array} props.images - Array of image objects.
 * @param {Function} props.onRemove - Callback to remove an image by index.
 */
function ImageAttachmentList({ images, onRemove }) {
  if (!images || images.length === 0) {
    return null;
  }

  return (
    <div className="flex gap-2 overflow-x-auto pt-3 pb-2 px-3">
      {images.map((image, index) => (
        <ImageAttachment
          key={`${image.source}-${image.source === "browser" ? image.file.name : image.path}-${index}`}
          image={image}
          onRemove={onRemove}
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
};

export default ImageAttachmentList;
