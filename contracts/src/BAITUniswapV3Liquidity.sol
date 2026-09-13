// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "./WBAIT.sol";

/**
 * @title IUniswapV3Factory — Minimal interface stub
 */
interface IUniswapV3Factory {
    function getPool(address tokenA, address tokenB, uint24 fee) external view returns (address);
    function createPool(address tokenA, address tokenB, uint24 fee) external returns (address);
}

/**
 * @title IUniswapV3Pool — Minimal interface stub
 */
interface IUniswapV3Pool {
    function initialize(uint160 sqrtPriceX96) external;
    function token0() external view returns (address);
    function token1() external view returns (address);
    function fee() external view returns (uint24);
}

/**
 * @title INonfungiblePositionManager — Minimal interface stub for minting
 */
interface INonfungiblePositionManager {
    struct MintParams {
        address token0;
        address token1;
        uint24 fee;
        int24 tickLower;
        int24 tickUpper;
        uint256 amount0Desired;
        uint256 amount1Desired;
        uint256 amount0Min;
        uint256 amount1Min;
        address recipient;
        uint256 deadline;
    }

    function mint(MintParams calldata params) external returns (
        uint256 tokenId,
        uint128 liquidity,
        uint256 amount0,
        uint256 amount1
    );
}

/**
 * @title BAITUniswapV3Liquidity — Uniswap V3 Pool Bootstrapper
 * @notice Creates and seeds the wBAIT/WETH pool on Uniswap V3
 *         Fee tier: 0.3% (tier 60 tick spacing)
 *         Initial price: ~$0.00111071/BAIT
 */
contract BAITUniswapV3Liquidity is Ownable2Step {
    WBAIT public immutable wbait;
    IUniswapV3Factory public immutable factory;
    INonfungiblePositionManager public immutable positionManager;

    address public immutable WETH;
    uint24 public constant FEE_TIER = 3000; // 0.3%
    int24 public constant TICK_SPACING = 60;

    // Initial sqrt price for ~$0.00111071/BAIT (WETH as quote)
    uint160 public constant INITIAL_SQRT_PRICE = 2190640149935016301856;

    uint256 public positionTokenId;

    event PoolCreated(address indexed pool, address token0, address token1, uint24 fee);
    event LiquidityAdded(uint256 indexed tokenId, uint128 liquidity, uint256 amount0, uint256 amount1);

    constructor(
        address _wbait,
        address _factory,
        address _positionManager,
        address _weth
    ) Ownable(msg.sender) {
        wbait = WBAIT(_wbait);
        factory = IUniswapV3Factory(_factory);
        positionManager = INonfungiblePositionManager(_positionManager);
        WETH = _weth;
    }

    /**
     * @notice Create wBAIT/WETH pool if it doesn't exist
     */
    function createPool() external onlyOwner returns (address pool) {
        pool = factory.getPool(address(wbait), WETH, FEE_TIER);
        if (pool == address(0)) {
            pool = factory.createPool(address(wbait), WETH, FEE_TIER);
            IUniswapV3Pool(pool).initialize(INITIAL_SQRT_PRICE);
            emit PoolCreated(pool, address(wbait), WETH, FEE_TIER);
        }
    }

    /**
     * @notice Add concentrated liquidity to the pool with slippage protection
     * @param amountWBAIT Amount of wBAIT to add
     * @param amountWETH Amount of WETH to add
     * @param tickLower Lower tick bound
     * @param tickUpper Upper tick bound
     * @param amount0Min Minimum amount of token0 to receive (slippage protection, MUST be > 0)
     * @param amount1Min Minimum amount of token1 to receive (slippage protection, MUST be > 0)
     */
    function addLiquidity(
        uint256 amountWBAIT,
        uint256 amountWETH,
        int24 tickLower,
        int24 tickUpper,
        uint256 amount0Min,
        uint256 amount1Min
    ) external onlyOwner returns (uint256 tokenId, uint128 liquidity, uint256 amount0, uint256 amount1) {
        require(amount0Min > 0, "BAITUniswapV3: zero amount0Min");
        require(amount1Min > 0, "BAITUniswapV3: zero amount1Min");

        wbait.approve(address(positionManager), amountWBAIT);

        INonfungiblePositionManager.MintParams memory params = INonfungiblePositionManager.MintParams({
            token0: address(wbait) < WETH ? address(wbait) : WETH,
            token1: address(wbait) < WETH ? WETH : address(wbait),
            fee: FEE_TIER,
            tickLower: tickLower,
            tickUpper: tickUpper,
            amount0Desired: address(wbait) < WETH ? amountWBAIT : amountWETH,
            amount1Desired: address(wbait) < WETH ? amountWETH : amountWBAIT,
            amount0Min: amount0Min,
            amount1Min: amount1Min,
            recipient: address(this),
            deadline: block.timestamp + 300
        });

        (tokenId, liquidity, amount0, amount1) = positionManager.mint(params);
        positionTokenId = tokenId;

        emit LiquidityAdded(tokenId, liquidity, amount0, amount1);
    }
}
