// stringMath.cpp
// Usage examples:
//   stringMath -in "unboundColorClipboard: 1.0 1.0 1.0 1.0" -mult 255
//   stringMath -in "unboundColorClipboard: 255 255 255 255" -div 255
//
// Behavior:
// - Rewrites every numeric token in the input (ints/floats/scientific, signed)
// - Applies multiply OR divide (exactly one must be provided)
// - Outputs floats (always includes a decimal point)

#include <iostream>
#include <string>
#include <iomanip>
#include <cstdlib>
#include <cerrno>
#include <cctype>

static void usage() {
    std::cout <<
        "stringMath - apply multiply/divide to all numbers in a string\n"
        "Usage:\n"
        "  stringMath [-in \"TEXT\"] (-mult X | -div X)\n"
        "If -in is omitted, reads from stdin (all lines).\n";
}

static bool parse_double(const std::string& s, double& out) {
    errno = 0;
    char* end = nullptr;
    out = std::strtod(s.c_str(), &end);
    if (end == s.c_str()) return false;
    if (errno == ERANGE) return false;
    // Allow trailing whitespace only
    while (*end) {
        if (!std::isspace(static_cast<unsigned char>(*end))) return false;
        ++end;
    }
    return true;
}

// Detect number start: digit or '.' or sign followed by digit/dot
static bool is_number_start(const std::string& s, size_t i) {
    char c = s[i];
    if (std::isdigit(static_cast<unsigned char>(c)) || c == '.') return true;
    if ((c == '+' || c == '-') && i + 1 < s.size()) {
        char n = s[i + 1];
        return (std::isdigit(static_cast<unsigned char>(n)) || n == '.');
    }
    return false;
}

// Parse a numeric token starting at i using strtod; returns length in 'len'
static bool read_number_token(const std::string& s, size_t i, size_t& len, double& val) {
    const char* start = s.c_str() + i;
    char* end = nullptr;
    errno = 0;
    val = std::strtod(start, &end);
    if (end == start) return false;
    if (errno == ERANGE) return false;
    len = static_cast<size_t>(end - start);
    return len > 0;
}

static std::string format_float(double v) {
    // Always show a decimal point, like 255.0, 1.0
    std::ostringstream oss;
    oss.setf(std::ios::fixed);
    oss << std::setprecision(6) << v; // keep it stable; we'll trim trailing zeros
    std::string out = oss.str();

    // Trim trailing zeros but keep one digit after decimal
    // e.g. "1.000000" -> "1.0", "0.125000" -> "0.125"
    auto dot = out.find('.');
    if (dot != std::string::npos) {
        // remove trailing zeros
        while (!out.empty() && out.back() == '0') out.pop_back();
        // if ends with '.', add '0'
        if (!out.empty() && out.back() == '.') out.push_back('0');
    } else {
        out += ".0";
    }
    return out;
}

static std::string process_line(const std::string& line, bool doMult, double factor) {
    std::string out;
    out.reserve(line.size() + 16);

    for (size_t i = 0; i < line.size(); ) {
        if (is_number_start(line, i)) {
            size_t len = 0;
            double val = 0.0;
            if (read_number_token(line, i, len, val)) {
                double result = doMult ? (val * factor) : (val / factor);
                out += format_float(result);
                i += len;
                continue;
            }
        }
        out.push_back(line[i]);
        ++i;
    }
    return out;
}

int main(int argc, char* argv[]) {
    std::string inText;
    bool haveInText = false;

    bool haveMult = false, haveDiv = false;
    double multVal = 0.0, divVal = 0.0;

    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];

        if ((a == "-in" || a == "--in") && i + 1 < argc) {
            inText = argv[++i];
            haveInText = true;
        } else if (a == "-mult" && i + 1 < argc) {
            std::string v = argv[++i];
            if (!parse_double(v, multVal)) {
                std::cerr << "stringMath: invalid -mult value: " << v << "\n";
                return 2;
            }
            haveMult = true;
        } else if (a == "-div" && i + 1 < argc) {
            std::string v = argv[++i];
            if (!parse_double(v, divVal)) {
                std::cerr << "stringMath: invalid -div value: " << v << "\n";
                return 2;
            }
            haveDiv = true;
        } else if (a == "-h" || a == "--help") {
            usage();
            return 0;
        } else {
            std::cerr << "stringMath: unknown arg: " << a << "\n";
            usage();
            return 2;
        }
    }

    if (haveMult == haveDiv) {
        std::cerr << "stringMath: provide exactly one of -mult or -div\n";
        return 2;
    }

    bool doMult = haveMult;
    double factor = doMult ? multVal : divVal;
    if (factor == 0.0) {
        std::cerr << "stringMath: factor must not be 0\n";
        return 2;
    }

    if (haveInText) {
        std::cout << process_line(inText, doMult, factor) << "\n";
        return 0;
    }

    // Filter mode: read stdin line by line
    std::string line;
    while (std::getline(std::cin, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        std::cout << process_line(line, doMult, factor) << "\n";
    }
    return 0;
}