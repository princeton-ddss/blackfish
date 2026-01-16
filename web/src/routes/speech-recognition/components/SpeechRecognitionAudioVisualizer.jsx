"use-client";

import { useState, useEffect } from "react";
import { AudioVisualizer } from "react-audio-visualize";
import { blackfishApiURL } from "@/config";
import PropTypes from "prop-types";

function SpeechRecognitionAudioVisualizer({ audioPath }) {
  const [blob, setBlob] = useState(null);
  // const visualizerRef = useRef < HTMLCanvasElement > null;

  useEffect(() => {
    const fetchAudio = async () => {
      const url = `${blackfishApiURL}/api/audio?path=${audioPath}`;
      const res = await fetch(url, { method: "GET" });
      const blob = await res.blob();
      setBlob(blob);
    };
    if (audioPath) {
      fetchAudio();
    } else {
      setBlob(null);
    }
  }, [audioPath]);

  if (blob) {
    return (
      <div className="bg-white w-full">
        <AudioVisualizer
          // ref={visualizerRef}
          blob={blob}
          width={700}
          height={150}
          barWidth={1}
          gap={1}
          barColor={"#52B3F0"}
        />
      </div>
    );
  } else {
    return <div></div>;
  }
}

SpeechRecognitionAudioVisualizer.propTypes = {
  audioPath: PropTypes.string,
};

export default SpeechRecognitionAudioVisualizer;
