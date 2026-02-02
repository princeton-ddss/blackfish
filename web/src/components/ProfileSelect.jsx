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
      <MenuButton className="flex items-center gap-1.5 rounded-md bg-white pl-3 pr-1 py-1.5 text-sm font-light text-gray-700 hover:bg-gray-50 focus:outline-none dark:text-gray-300 dark:hover:text-gray-200 dark:bg-gray-900">
        {!selectedProfile && (
          <ExclamationTriangleIcon className="h-4 w-4 text-yellow-400" aria-hidden="true" />
        )}
        <span>Profile</span>
        <ChevronDownIcon className="h-4 w-4 text-gray-400" aria-hidden="true" />
      </MenuButton>

      <MenuItems
        anchor="bottom end"
        className="absolute right-0 z-50 mt-1 w-72 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none dark:bg-gray-700"
      >
        <div className="py-1">
          {profiles.map((profile) => (
            <MenuItem key={profile.name}>
              <button
                onClick={() => setSelectedProfile(profile)}
                className="group flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 data-[focus]:bg-gray-100 data-[focus]:text-gray-900 dark:text-gray-300 data-[focus]:dark:bg-gray-800"
              >
                <span className={isSelected(profile) ? "font-semibold" : "font-normal"}>
                  {profile.name}
                </span>
                <span className="text-gray-400 font-light">
                  @{profile.host || "localhost"}
                </span>
                {isSelected(profile) && (
                  <CheckIcon className="ml-auto h-4 w-4 text-blue-600" aria-hidden="true" />
                )}
              </button>
            </MenuItem>
          ))}
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
