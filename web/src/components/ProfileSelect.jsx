import { createContext, useState, useEffect } from "react";
import {
  Menu,
  MenuButton,
  MenuItem,
  MenuItems
} from "@headlessui/react";
import { CheckIcon, ChevronDownIcon } from "@heroicons/react/20/solid";
import { useProfiles } from "@/lib/loaders";
import { ExclamationTriangleIcon } from "@heroicons/react/24/solid";
import PropTypes from "prop-types";

const ProfileContext = createContext();

/**
 * Profile provider component.
 * @param {object} options
 * @param {JSX.Element} options.children
 * @return {JSX.Element}
 */
const ProfileProvider = ({ children }) => {
  const [profile, setProfileContext] = useState(null);

  useEffect(() => {
    const data = localStorage.getItem("profile");
    const restoredProfile = data ? JSON.parse(data) : null;
    console.debug("Restored profile", restoredProfile);
    setProfileContext(restoredProfile);
  }, []);

  const setProfile = (profile) => {
    localStorage.setItem("profile", JSON.stringify(profile));
    setProfileContext(profile);
  };

  return (
    <ProfileContext.Provider value={{ profile, setProfile }}>
      {children}
    </ProfileContext.Provider>
  );
}

ProfileProvider.propTypes = {
  children: PropTypes.node
};


/**
 * Profile Select component.
 * @param {object} options
 * @param {object} options.selectedProfile
 * @param {Function} options.setSelectedProfile
 * @return {JSX.Element}
 */
function ProfileSelect({
  selectedProfile,
  setSelectedProfile
}) {
  const { profiles, error, isLoading } = useProfiles();

  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5 rounded-md bg-white pl-3 pr-1 py-1.5 text-sm font-light text-gray-400 dark:text-gray-500 dark:bg-gray-900">
        <span className="animate-pulse">Profile</span>
        <ChevronDownIcon className="h-4 w-4 text-gray-300 dark:text-gray-600" aria-hidden="true" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-1.5 rounded-md bg-white pl-3 pr-1 py-1.5 text-sm font-light text-red-500 dark:bg-gray-900">
        <ExclamationTriangleIcon className="h-4 w-4" aria-hidden="true" />
        <span>Error</span>
      </div>
    );
  }

  if (profiles.length === 0) {
    return (
      <div className="flex items-center gap-1.5 rounded-md bg-white pl-3 pr-1 py-1.5 text-sm font-light text-gray-500 dark:text-gray-400 dark:bg-gray-900">
        <span>No profiles</span>
      </div>
    );
  }

  const isSelected = (profile) => selectedProfile?.name === profile.name;

  return (
    <Menu as="div" className="relative">
      {
        selectedProfile && !profiles.map(x => x.name).includes(selectedProfile.name) &&
        <div>
          {/* TODO: add Alert */}
          Profile is missing.
        </div>
      }
      <MenuButton className="flex items-center gap-2 rounded-md bg-white pl-4 pr-3 py-2.5 text-sm font-light text-gray-700 focus:outline-none dark:text-gray-300 dark:hover:text-gray-200 dark:bg-gray-900">
        {!selectedProfile && (
          <ExclamationTriangleIcon className="h-4 w-4 text-yellow-400" aria-hidden="true" />
        )}
        <span>{selectedProfile ? (selectedProfile.host ? `${selectedProfile.user}@${selectedProfile.host}` : "localhost") : "Profile"}</span>
        <ChevronDownIcon className="h-4 w-4 text-gray-400" aria-hidden="true" />
      </MenuButton>

      <MenuItems
        anchor="bottom end"
        className="absolute right-0 z-50 mt-0.5 w-80 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none dark:bg-gray-700"
      >
        <div>
          {profiles.map((profile, index) => {
            const isFirst = index === 0;
            const isLast = index === profiles.length - 1;
            return (
            <MenuItem key={profile.name} className="w-full">
              <button
                onClick={() => setSelectedProfile(profile)}
                className={`group flex w-full items-center justify-between px-3 py-2 text-left transition-colors hover:!bg-blue-500 ${
                  isFirst ? "rounded-t-md" : ""
                } ${isLast ? "rounded-b-md" : ""} ${
                  isSelected(profile) ? "bg-gray-50 dark:bg-gray-600" : ""
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100 group-hover:text-white">
                      {profile.name}
                    </span>
                    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${
                      profile.schema === "slurm"
                        ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                        : "bg-gray-100 dark:bg-gray-600 text-gray-600 dark:text-gray-300"
                    } group-hover:bg-blue-400 group-hover:text-white`}>
                      {profile.schema}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 group-hover:text-blue-100">
                    {profile.host ? `${profile.user}@${profile.host}` : "localhost"}
                  </div>
                </div>
                {isSelected(profile) && (
                  <CheckIcon className="h-4 w-4 text-blue-600 dark:text-blue-400 group-hover:text-white" aria-hidden="true" />
                )}
              </button>
            </MenuItem>
          );
          })}
        </div>
      </MenuItems>
    </Menu>
  )
}

ProfileSelect.propTypes = {
  selectedProfile: PropTypes.object,
  setSelectedProfile: PropTypes.func
};

export default ProfileSelect;
export { ProfileContext, ProfileProvider };
