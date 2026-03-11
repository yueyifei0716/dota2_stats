"use client";

import { useState } from "react";
import { updateData, calibrateMmr } from "@/lib/api";

export default function UpdateButton({ onUpdated }: { onUpdated?: () => void }) {
  const [updating, setUpdating] = useState(false);
  const [message, setMessage] = useState("");
  const [showMmr, setShowMmr] = useState(false);
  const [mmrValue, setMmrValue] = useState("");

  const handleUpdate = async () => {
    setUpdating(true);
    setMessage("");
    try {
      const res = await updateData();
      setMessage(res.message);
      if (res.success) onUpdated?.();
    } catch {
      setMessage("更新失败");
    }
    setUpdating(false);
  };

  const handleCalibrate = async () => {
    if (!mmrValue) return;
    try {
      await calibrateMmr(Number(mmrValue));
      setMessage("MMR 已校准");
      setShowMmr(false);
      setMmrValue("");
      onUpdated?.();
    } catch {
      setMessage("校准失败");
    }
  };

  return (
    <div className="fixed bottom-6 right-6 flex flex-col items-end gap-2 z-50">
      {message && (
        <div className="bg-gray-800 border border-white/20 rounded-lg px-4 py-2 text-sm shadow-lg">
          {message}
        </div>
      )}
      {showMmr && (
        <div className="bg-gray-800 border border-white/20 rounded-lg p-3 shadow-lg flex gap-2">
          <input
            type="number"
            value={mmrValue}
            onChange={(e) => setMmrValue(e.target.value)}
            placeholder="输入 MMR"
            className="bg-white/10 border border-white/20 rounded px-2 py-1 text-sm w-24 text-white"
          />
          <button onClick={handleCalibrate} className="bg-yellow-500 text-gray-900 rounded px-3 py-1 text-sm font-bold hover:bg-yellow-400">
            校准
          </button>
        </div>
      )}
      <div className="flex gap-2">
        <button
          onClick={() => setShowMmr(!showMmr)}
          className="bg-gray-700 hover:bg-gray-600 text-white rounded-full w-12 h-12 flex items-center justify-center shadow-lg text-lg"
          title="校准 MMR"
        >
          🎯
        </button>
        <button
          onClick={handleUpdate}
          disabled={updating}
          className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-400 hover:to-purple-500 text-white rounded-full w-12 h-12 flex items-center justify-center shadow-lg disabled:opacity-50 text-lg"
          title="更新数据"
        >
          {updating ? "⏳" : "🔄"}
        </button>
      </div>
    </div>
  );
}
