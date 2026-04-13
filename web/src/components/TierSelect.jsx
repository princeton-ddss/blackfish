import PropTypes from "prop-types";
import { CheckCircleIcon, CpuChipIcon } from "@heroicons/react/20/solid";

function TierCard({ tier, isSelected, isRecommended, onClick, disabled }) {
  const gpuDisplay = tier.gpu_count > 0
    ? `${tier.gpu_count}x ${tier.gpu_type || "GPU"}`
    : "CPU Only";

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`
        relative flex flex-col p-4 rounded-lg border text-left transition-all
        ${isSelected
          ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30"
          : "border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500"
        }
        ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
      `}
    >
      {/* Selected indicator */}
      {isSelected && (
        <CheckCircleIcon
          className="absolute top-2 right-2 h-5 w-5 text-blue-500"
          aria-hidden="true"
        />
      )}

      {/* Recommended badge */}
      {isRecommended && !isSelected && (
        <span className="absolute top-2 right-2 inline-flex items-center rounded-full bg-green-100 dark:bg-green-900 px-2 py-0.5 text-xs font-medium text-green-800 dark:text-green-300">
          Recommended
        </span>
      )}

      {/* Tier name */}
      <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{tier.name}</h3>

      {/* Description */}
      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">{tier.description}</p>

      {/* Specs */}
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-600 dark:text-gray-300">
        <span className="inline-flex items-center gap-1">
          <CpuChipIcon className="h-3.5 w-3.5" />
          {gpuDisplay}
        </span>
        <span>{tier.cpu_cores} CPU</span>
        <span>{tier.memory_gb} GB</span>
      </div>
    </button>
  );
}

TierCard.propTypes = {
  tier: PropTypes.shape({
    name: PropTypes.string.isRequired,
    description: PropTypes.string,
    gpu_count: PropTypes.number,
    gpu_type: PropTypes.string,
    cpu_cores: PropTypes.number,
    memory_gb: PropTypes.number,
  }).isRequired,
  isSelected: PropTypes.bool,
  isRecommended: PropTypes.bool,
  onClick: PropTypes.func,
  disabled: PropTypes.bool,
};

function TierSelect({ tiers, selectedTier, recommendedTier, setSelectedTier, disabled }) {
  if (!tiers || tiers.length === 0) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400 italic">
        No resource tiers configured for this partition.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {tiers.map((tier) => (
        <TierCard
          key={tier.name}
          tier={tier}
          isSelected={selectedTier === tier.name}
          isRecommended={recommendedTier === tier.name && selectedTier !== tier.name}
          onClick={() => setSelectedTier(tier.name)}
          disabled={disabled}
        />
      ))}
    </div>
  );
}

TierSelect.propTypes = {
  tiers: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      description: PropTypes.string,
      gpu_count: PropTypes.number,
      gpu_type: PropTypes.string,
      cpu_cores: PropTypes.number,
      memory_gb: PropTypes.number,
    })
  ),
  selectedTier: PropTypes.string,
  recommendedTier: PropTypes.string,
  setSelectedTier: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};

export default TierSelect;
