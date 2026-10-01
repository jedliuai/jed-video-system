import { CSSProperties } from "react";
import {
  AbsoluteFill,
  CanvasImage,
  Easing,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import {
  editorialTalkingHeadDefault,
  type EditorialTalkingHeadContent,
} from "./content";

// Implemented by Codex from AGY's actual review, not an unverified model comparison.
// Exact design response and constraints are retained in design/agy/.
const colors = {
  ink: "#081224",
  blue: "#2D6BFF",
  gold: "#F5B642",
  white: "#F7F9FC",
  muted: "#A8B4C7",
};
const enterStyle = (
  frame: number,
  start: number,
  duration = 12,
): CSSProperties => {
  const progress = interpolate(frame, [start, start + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return {
    opacity: progress,
    transform: `translateY(${(1 - progress) * 10}px)`,
  };
};

export type AgyTalkingHeadSceneProps = {
  content?: EditorialTalkingHeadContent;
};

export const AgyTalkingHeadScene = ({
  content = editorialTalkingHeadDefault,
}: AgyTalkingHeadSceneProps) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        fontFamily: "JedSans",
        color: colors.white,
        backgroundColor: colors.ink,
      }}
    >
      <CanvasImage
        src={staticFile(content.background)}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(90deg, rgba(8,18,36,.98) 0%, rgba(8,18,36,.96) 24%, rgba(8,18,36,.60) 34%, rgba(8,18,36,0) 48%, rgba(8,18,36,0) 74%, rgba(8,18,36,.65) 82%, rgba(8,18,36,.92) 100%)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(8,18,36,.35) 0%, transparent 20%, transparent 80%, rgba(8,18,36,.2) 100%)",
        }}
      />

      <div
        style={{
          position: "absolute",
          left: 96,
          top: 72,
          display: "flex",
          alignItems: "baseline",
          gap: 12,
          ...enterStyle(frame, 0, 10),
        }}
      >
        <span style={{ fontSize: 46, fontWeight: 700, letterSpacing: -2 }}>
          Jed
        </span>
        <span
          style={{
            width: 9,
            height: 9,
            borderRadius: 9,
            backgroundColor: colors.blue,
          }}
        />
        <span
          style={{
            fontSize: 18,
            color: colors.muted,
            letterSpacing: 3,
            marginLeft: 13,
          }}
        >
          VISUAL NOTES
        </span>
      </div>
      <div
        style={{
          position: "absolute",
          right: 70,
          top: 89,
          color: colors.muted,
          fontSize: 20,
          letterSpacing: 2,
          ...enterStyle(frame, 0, 10),
        }}
      >
        B / 编辑感
      </div>

      <div style={{ position: "absolute", left: 96, top: 220, width: 520 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            ...enterStyle(frame, 0, 10),
          }}
        >
          <span
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: colors.blue,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            01
          </span>
          <span
            style={{ width: 32, height: 1, backgroundColor: colors.blue }}
          />
          <span
            style={{ fontSize: 20, letterSpacing: 1.2, color: colors.muted }}
          >
            {content.eyebrow}
          </span>
        </div>
        <div
          style={{
            marginTop: 44,
            fontSize: 56,
            fontWeight: 700,
            lineHeight: 1.34,
            letterSpacing: -1,
          }}
        >
          {content.headline.map((line, index) => (
            <div
              key={`${index}-${line}`}
              style={{
                ...enterStyle(frame, 8 + index * 8),
                color:
                  index === content.headline.length - 1
                    ? colors.gold
                    : colors.white,
              }}
            >
              {line}
            </div>
          ))}
        </div>
        <div
          style={{
            marginTop: 40,
            fontSize: 20,
            color: colors.muted,
            letterSpacing: 1,
            ...enterStyle(frame, 22, 10),
          }}
        >
          {content.footer}
        </div>
      </div>

      <div style={{ position: "absolute", left: 1520, top: 240, width: 330 }}>
        <div
          style={{
            paddingBottom: 26,
            fontSize: 18,
            letterSpacing: 3,
            color: colors.muted,
            borderBottom: "1px solid rgba(168,180,199,.22)",
            ...enterStyle(frame, 22, 10),
          }}
        >
          BUILD THE IDEA
        </div>
        {content.points.map((point, index) => (
          <div
            key={`${index}-${point.title}`}
            style={{
              paddingTop: 26,
              paddingBottom: 30,
              borderBottom: "1px solid rgba(168,180,199,.22)",
              ...enterStyle(frame, point.cueFrame),
            }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "32px minmax(0, 1fr)",
                gap: 14,
                alignItems: "baseline",
              }}
            >
              <span
                style={{
                  fontSize: 24,
                  fontWeight: 700,
                  fontVariantNumeric: "tabular-nums",
                  color:
                    index === content.points.length - 1
                      ? colors.gold
                      : colors.blue,
                }}
              >
                {String(index + 1).padStart(2, "0")}
              </span>
              <span
                style={{
                  fontSize: 34,
                  fontWeight: 700,
                  lineHeight: 1.38,
                  overflowWrap: "anywhere",
                }}
              >
                {point.title}
              </span>
            </div>
            {point.detail && (
              <div
                style={{
                  marginLeft: 46,
                  marginTop: 10,
                  fontSize: 24,
                  fontWeight: 400,
                  lineHeight: 1.5,
                  color: colors.muted,
                  overflowWrap: "anywhere",
                }}
              >
                {point.detail}
              </div>
            )}
          </div>
        ))}
      </div>
      <div
        style={{
          position: "absolute",
          left: 96,
          top: 1010,
          fontSize: 18,
          color: colors.muted,
          letterSpacing: 1,
        }}
      >
        样式预览 / 非成片
      </div>
    </AbsoluteFill>
  );
};
