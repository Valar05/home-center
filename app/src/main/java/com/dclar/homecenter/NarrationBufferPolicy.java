package com.dclar.homecenter;

import java.util.List;

final class NarrationBufferPolicy {
    private NarrationBufferPolicy() { }
    static double requiredAheadSeconds(List<Double> productionRatios, double remainingEstimatedAudioSeconds) {
        if (productionRatios == null || productionRatios.isEmpty()) return 15.0;
        int start = Math.max(0, productionRatios.size() - 8);
        double minimum = Double.POSITIVE_INFINITY;
        for (int i = start; i < productionRatios.size(); i++) {
            double value = productionRatios.get(i) == null ? 0.0 : productionRatios.get(i);
            if (Double.isFinite(value) && value > 0.0) minimum = Math.min(minimum, value);
        }
        if (!Double.isFinite(minimum)) return 15.0;
        double safeRate = 0.8 * minimum;
        return 5.0 + Math.max(0.0, Math.max(0.0, remainingEstimatedAudioSeconds) * (1.0 / safeRate - 1.0));
    }
}
